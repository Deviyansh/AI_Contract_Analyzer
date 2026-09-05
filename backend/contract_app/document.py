import re
from pathlib import Path

def extract_text(uploaded_file):
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="replace")
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document
        import io
        doc = Document(io.BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError("Unsupported file type. Use PDF, DOCX, or TXT.")

def segment_clauses(text, min_chars=50, max_chars=4000):
    """
    Split extracted contract text into likely contractual clauses.

    The segmenter:
    - removes leading document metadata before the first
      numbered clause when a numbered structure is detected
    - preserves numbered and lettered clause boundaries
    - ignores very short blocks
    - splits oversized clauses into sentence-based chunks
    """

    text = text.replace("\r", "\n")

    # Normalize excessive blank lines while preserving
    # line boundaries needed for clause detection.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    # --------------------------------------------------------
    # Detect whether the document has numbered clauses.
    # Examples:
    #
    # 1. Services
    # 2. Fees
    # 3. Intellectual Property
    #
    # Also supports:
    # (1) Services
    # 1) Services
    # 1.1 Services
    # --------------------------------------------------------

    numbered_pattern = re.compile(
        r"^\s*\(?\d+(?:\.\d+){0,4}\)?[.)]\s+",
        re.MULTILINE,
    )

    numbered_matches = list(
        numbered_pattern.finditer(text)
    )

    if numbered_matches:
        # If numbered clauses exist, discard everything
        # before the first numbered clause.
        #
        # This prevents:
        # "SOFTWARE SERVICES AGREEMENT
        #  Effective Date...
        #  Provider...
        #  Customer..."
        #
        # from becoming Clause 1.
        text = text[
            numbered_matches[0].start():
        ]

    # --------------------------------------------------------
    # Split on likely clause boundaries.
    # --------------------------------------------------------

    blocks = re.split(
        r"\n\s*(?="
        r"(?:"
        r"\(?\d+(?:\.\d+){0,4}\)?[.)]\s+"
        r"|"
        r"\(?[a-zA-Z]{1,3}\)?[.)]\s+"
        r"|"
        r"[-•*]\s+"
        r")"
        r")",
        text,
    )

    clauses = []

    for block in blocks:

        block = re.sub(
            r"\s+",
            " ",
            block,
        ).strip()

        if len(block) < min_chars:
            continue

        # ----------------------------------------------------
        # Normal-sized clause
        # ----------------------------------------------------

        if len(block) <= max_chars:
            clauses.append(block)
            continue

        # ----------------------------------------------------
        # Oversized clause:
        # split on sentence boundaries.
        # ----------------------------------------------------

        sentences = re.split(
            r"(?<=[.!?])\s+",
            block,
        )

        buffer = ""

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            candidate = (
                f"{buffer} {sentence}"
            ).strip()

            if len(candidate) <= max_chars:
                buffer = candidate

            else:

                if len(buffer) >= min_chars:
                    clauses.append(buffer)

                buffer = sentence

        if len(buffer) >= min_chars:
            clauses.append(buffer)

    return clauses