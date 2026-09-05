from pathlib import Path
import ast
import json
import random
import re

import pandas as pd


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parents[2]

ORIGINAL = BASE / "data" / "all_reshaped_clauses.csv"
SYNTHETIC = BASE / "data" / "curated_synthetic_clauses.csv"

CUAD_DIR = BASE / "data" / "external" / "cuad"
CUAD_MASTER = CUAD_DIR / "master_clauses.csv"

PROCESSED = BASE / "data" / "processed"

TRAIN_OUT = PROCESSED / "augmented_clauses.csv"
CUAD_TEST_OUT = PROCESSED / "cuad_external_test.csv"


# ============================================================
# CONFIG
# ============================================================

RANDOM_SEED = 42
CUAD_TEST_RATIO = 0.20

MIN_CHARS = 40
MAX_CHARS = 8500

# Prevent CUAD from overwhelming the original dataset.
# The cap is applied ONLY to CUAD training data.
CUAD_MAX_PER_LABEL = 500


# ============================================================
# TARGET LABELS
# ============================================================

TARGET_LABELS = {
    "Assignment",
    "Audit Rights",
    "Auto-Renewal",
    "Change of Control",
    "Confidentiality",
    "Dispute Resolution",
    "Exclusivity",
    "Force Majeure",
    "Governing Law",
    "Indemnification",
    "Insurance",
    "Intellectual Property",
    "Liability",
    "Non-Compete",
    "Payment Terms",
    "Termination",
    "Warranty",
}


# ============================================================
# HIGH-CONFIDENCE CUAD MAPPINGS ONLY
# ============================================================

CUAD_MAP = {
    # Governing law
    "Governing Law": "Governing Law",

    # Renewal
    "Renewal Term": "Auto-Renewal",
    "Notice Period To Terminate Renewal": "Auto-Renewal",

    # Restrictive covenants
    "Non-Compete": "Non-Compete",
    "Competitive Restriction Exception": "Non-Compete",

    # Exclusivity
    "Exclusivity": "Exclusivity",

    # Termination
    "Termination For Convenience": "Termination",

    # Change of control
    "Change Of Control": "Change of Control",

    # Assignment
    "Anti-Assignment": "Assignment",

    # Intellectual property
    "Ip Ownership Assignment": "Intellectual Property",
    "Joint Ip Ownership": "Intellectual Property",
    "License Grant": "Intellectual Property",
    "Non-Transferable License": "Intellectual Property",
    "Affiliate License-Licensor": "Intellectual Property",
    "Affiliate License-Licensee": "Intellectual Property",
    "Unlimited/All-You-Can-Eat-License": "Intellectual Property",
    "Irrevocable Or Perpetual License": "Intellectual Property",

    # Audit
    "Audit Rights": "Audit Rights",

    # Liability
    "Uncapped Liability": "Liability",
    "Cap On Liability": "Liability",
    "Liquidated Damages": "Liability",

    # Warranty
    "Warranty Duration": "Warranty",

    # Insurance
    "Insurance": "Insurance",
}


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(value):
    """
    Normalize text without changing its legal meaning.
    """
    if value is None:
        return ""

    text = str(value)

    # Common encoding artifacts
    replacements = {
        "\\u2019": "'",
        "\\u2018": "'",
        "\\u201c": '"',
        "\\u201d": '"',
        "‚Äô": "'",
        "‚Äú": '"',
        "‚Äù": '"',
        "‚Äì": "-",
        "‚Äî": "-",
        "√©": "e",
        "√¥": "o",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # Remove trailing page marker if present
    text = re.sub(r"\(Page\s*\d+\)\s*$", "", text, flags=re.I)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    # Remove wrapping quotes only
    text = text.strip(" \"'")

    return text.strip()


def normalize_for_dedup(text):
    """
    Normalization used ONLY for duplicate detection.
    """
    text = clean_text(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ============================================================
# CUAD CELL PARSING
# ============================================================

def parse_cuad_cell(value):
    """
    CUAD answer cells can appear as:
      - empty strings
      - []
      - JSON/Python lists
      - plain strings
      - lists of dictionaries

    Return a clean list of text spans.
    """

    if value is None:
        return []

    text = str(value).strip()

    if not text:
        return []

    if text.lower() in {
        "nan",
        "none",
        "no",
        "[]",
        "{}",
        "null",
    }:
        return []

    # Try JSON / Python list representation
    if text.startswith("[") and text.endswith("]"):
        parsed = None

        try:
            parsed = json.loads(text)
        except Exception:
            try:
                parsed = ast.literal_eval(text)
            except Exception:
                parsed = None

        if isinstance(parsed, list):
            results = []

            for item in parsed:
                if isinstance(item, dict):
                    candidate = (
                        item.get("text")
                        or item.get("answer")
                        or item.get("context")
                    )

                    if candidate:
                        results.append(str(candidate))

                elif item is not None:
                    results.append(str(item))

            return results

    return [text]


# ============================================================
# DATA VALIDATION
# ============================================================

def clean_frame(df):
    """
    Standardize dataframe rows.
    """

    required = {"label", "text", "source", "group_id"}

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    df = df.copy()

    df["text"] = df["text"].map(clean_text)
    df["label"] = df["label"].map(clean_text)
    df["source"] = df["source"].map(clean_text)
    df["group_id"] = df["group_id"].map(clean_text)

    # Valid target labels only
    df = df[df["label"].isin(TARGET_LABELS)]

    # Length filtering
    df = df[
        df["text"].str.len().between(
            MIN_CHARS,
            MAX_CHARS
        )
    ]

    # Dedup helper
    df["_dedup_text"] = df["text"].map(normalize_for_dedup)

    df = df[df["_dedup_text"].str.len() > 0]

    return df


# ============================================================
# ORIGINAL DATA
# ============================================================

def load_original():
    print("\n[1/4] Loading original dataset...")

    if not ORIGINAL.exists():
        raise FileNotFoundError(
            f"Original dataset not found:\n{ORIGINAL}"
        )

    df = pd.read_csv(ORIGINAL)

    required = {
        "filename",
        "clause_type",
        "clause_text",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Original dataset is missing columns: "
            + str(sorted(missing))
        )

    df = df[
        df["clause_type"].isin(TARGET_LABELS)
    ].copy()

    df["label"] = df["clause_type"]
    df["text"] = df["clause_text"]
    df["source"] = "original"

    # IMPORTANT:
    # Preserve document identity for grouped evaluation.
    df["group_id"] = (
        "original:"
        + df["filename"].astype(str)
    )

    df = df[
        ["label", "text", "source", "group_id"]
    ]

    df = clean_frame(df)

    # Remove exact duplicates within original dataset
    df = df.drop_duplicates(
        subset=["_dedup_text"]
    )

    print(f"Original rows: {len(df)}")

    return df


# ============================================================
# SYNTHETIC DATA
# ============================================================

def load_synthetic():
    print("\n[2/4] Loading synthetic dataset...")

    if not SYNTHETIC.exists():
        raise FileNotFoundError(
            f"Synthetic dataset not found:\n{SYNTHETIC}"
        )

    df = pd.read_csv(SYNTHETIC)

    required = {"label", "text"}

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "Synthetic dataset is missing columns: "
            + str(sorted(missing))
        )

    df = df.copy()

    df["source"] = "synthetic"

    # Every synthetic row is treated as its own group.
    # This prevents synthetic examples from accidentally
    # being grouped with real contracts.
    df["group_id"] = (
        "synthetic:"
        + df.index.astype(str)
    )

    df = df[
        ["label", "text", "source", "group_id"]
    ]

    df = clean_frame(df)

    df = df.drop_duplicates(
        subset=["_dedup_text"]
    )

    print(f"Synthetic rows: {len(df)}")

    return df


# ============================================================
# CUAD
# ============================================================

def load_cuad():
    print("\n[3/4] Loading CUAD...")

    if not CUAD_MASTER.exists():
        raise FileNotFoundError(
            f"CUAD file not found: {CUAD_MASTER}"
        )

    cdf = pd.read_csv(
        CUAD_MASTER,
        dtype=str
    ).fillna("")

    rows = []

    for cuad_column, target_label in CUAD_MAP.items():

        answer_column = f"{cuad_column}-Answer"

        if (
            cuad_column not in cdf.columns
            or answer_column not in cdf.columns
        ):
            print(
                f"Skipping missing CUAD columns: "
                f"{cuad_column}"
            )
            continue

        for _, row in cdf.iterrows():

            filename = str(
                row["Filename"]
            ).strip()

            answer = clean_text(
                row[answer_column]
            )

            context = clean_text(
                row[cuad_column]
            )

            if not filename or not answer:
                continue

            # "No" means this contract does not contain
            # the target clause.
            if answer.lower() == "no":
                continue

            # "Yes" means the clause exists.
            # Use the actual contextual passage rather
            # than training on the word "Yes".
            if answer.lower() == "yes":
                text = context
            else:
                # For answers such as "Nevada" or "2 years",
                # prefer the surrounding clause context.
                text = (
                    context
                    if len(context) >= MIN_CHARS
                    else answer
                )

            text = clean_text(text)

            if len(text) < MIN_CHARS:
                continue

            rows.append(
                {
                    "label": target_label,
                    "text": text,
                    "source": "cuad",
                    "group_id": f"cuad:{filename}",
                }
            )

    if not rows:
        raise RuntimeError(
            "No usable CUAD rows extracted."
        )

    df = pd.DataFrame(rows)

    df = clean_frame(df)

    # Remove exact duplicate text/label pairs.
    df = df.drop_duplicates(
        subset=["_dedup_text", "label"]
    )

    print(
        "CUAD extracted rows:",
        len(df)
    )

    print(
        "CUAD contracts:",
        df["group_id"].nunique()
    )

    # --------------------------------------------------------
    # Contract-level 80/20 split
    # --------------------------------------------------------

    groups = sorted(
        df["group_id"].unique()
    )

    rng = random.Random(
        RANDOM_SEED
    )

    rng.shuffle(groups)

    test_count = max(
        1,
        round(
            len(groups)
            * CUAD_TEST_RATIO
        )
    )

    test_groups = set(
        groups[:test_count]
    )

    train = df[
        ~df["group_id"].isin(test_groups)
    ].copy()

    test = df[
        df["group_id"].isin(test_groups)
    ].copy()

    print(
        "CUAD train contracts:",
        train["group_id"].nunique()
    )

    print(
        "CUAD test contracts:",
        test["group_id"].nunique()
    )

    print(
        "CUAD train rows:",
        len(train)
    )

    print(
        "CUAD test rows:",
        len(test)
    )

    return (
        train[
            [
                "label",
                "text",
                "source",
                "group_id",
            ]
        ],
        test[
            [
                "label",
                "text",
                "source",
                "group_id",
            ]
        ],
    )

# ============================================================
# REMOVE TRAINING DUPLICATES THAT APPEAR IN CUAD TEST
# ============================================================

def protect_test_set(train, test):
    """
    Never allow an exact CUAD-test clause to appear in
    training data from another source.
    """

    train = train.copy()
    test = test.copy()

    train["_dedup_text"] = train[
        "text"
    ].map(normalize_for_dedup)

    test["_dedup_text"] = test[
        "text"
    ].map(normalize_for_dedup)

    test_texts = set(
        test["_dedup_text"]
    )

    before = len(train)

    train = train[
        ~train["_dedup_text"].isin(
            test_texts
        )
    ].copy()

    removed = before - len(train)

    if removed:
        print(
            "Training rows removed because "
            f"they overlap CUAD test: {removed}"
        )

    train.drop(
        columns=["_dedup_text"],
        inplace=True,
        errors="ignore"
    )

    test.drop(
        columns=["_dedup_text"],
        inplace=True,
        errors="ignore"
    )

    return train, test


# ============================================================
# MAIN
# ============================================================

def main():

    PROCESSED.mkdir(
        parents=True,
        exist_ok=True
    )

    print("=" * 70)
    print("AI CONTRACT ANALYZER - DATASET BUILDER")
    print("=" * 70)

    original = load_original()
    synthetic = load_synthetic()
    cuad_train, cuad_test = load_cuad()

    # --------------------------------------------------------
    # Combine training sources
    # --------------------------------------------------------

    train = pd.concat(
        [
            original,
            synthetic,
            cuad_train,
        ],
        ignore_index=True
    )

    train, cuad_test = protect_test_set(
        train,
        cuad_test
    )

    # --------------------------------------------------------
    # Final duplicate/conflict handling
    # --------------------------------------------------------

    train["_dedup_text"] = train[
        "text"
    ].map(normalize_for_dedup)

    # If the same normalized text has multiple labels,
    # it is ambiguous for the single-label classifier.
    label_counts = (
        train.groupby("_dedup_text")["label"]
        .nunique()
    )

    conflicting = set(
        label_counts[
            label_counts > 1
        ].index
    )

    if conflicting:
        print(
            "Training conflicting texts removed:",
            len(conflicting)
        )

        train = train[
            ~train["_dedup_text"].isin(
                conflicting
            )
        ].copy()

    # Keep one copy of each text.
    train = train.drop_duplicates(
        subset=["_dedup_text"]
    )

    train.drop(
        columns=["_dedup_text"],
        inplace=True,
        errors="ignore"
    )

    # Stable ordering
    train = train.sort_values(
        ["label", "source", "group_id"]
    ).reset_index(drop=True)

    cuad_test = cuad_test.sort_values(
        ["label", "group_id"]
    ).reset_index(drop=True)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    train.to_csv(
        TRAIN_OUT,
        index=False
    )

    cuad_test.to_csv(
        CUAD_TEST_OUT,
        index=False
    )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("DATASET BUILD COMPLETE")
    print("=" * 70)

    print(
        f"\nTraining dataset:\n{TRAIN_OUT}"
    )

    print(
        f"CUAD external test:\n{CUAD_TEST_OUT}"
    )

    print(
        "\nTraining rows:",
        len(train)
    )

    print(
        "Training contracts/groups:",
        train["group_id"].nunique()
    )

    print(
        "\nTraining by source:"
    )

    print(
        train["source"]
        .value_counts()
        .to_string()
    )

    print(
        "\nTraining by label:"
    )

    print(
        train["label"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print(
        "\nCUAD test rows:",
        len(cuad_test)
    )

    print(
        "CUAD test contracts:",
        cuad_test["group_id"].nunique()
    )

    print(
        "\nCUAD test by label:"
    )

    print(
        cuad_test["label"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nDone.")


if __name__ == "__main__":
    main()