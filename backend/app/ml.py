from pathlib import Path
from functools import lru_cache

import joblib

from ..contract_app.document import extract_text, segment_clauses
from ..contract_app.risk_rules import detect_flags


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    BASE
    / "ml"
    / "artifacts"
    / "clause_classifier.joblib"
)

MODEL_VERSION = "tfidf-logreg-cuad-v2"


# ============================================================
# MODEL LOADING
# ============================================================

@lru_cache(maxsize=1)
def get_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Missing trained model at {MODEL_PATH}. "
            "Run ml/scripts/train_model.py first."
        )

    return joblib.load(MODEL_PATH)


# ============================================================
# MODEL INFORMATION
# ============================================================

def get_model_classes():
    return [
        str(x)
        for x in get_model().classes_
    ]


# ============================================================
# CLAUSE CLASSIFICATION
# ============================================================

def classify(text, top_k=3):

    model = get_model()

    probabilities = model.predict_proba(
        [text]
    )[0]

    ranked = sorted(
        zip(
            model.classes_,
            probabilities,
        ),
        key=lambda x: x[1],
        reverse=True,
    )

    top = ranked[:top_k]

    top_prob = float(top[0][1])

    margin = (
        float(top[0][1] - top[1][1])
        if len(top) > 1
        else top_prob
    )

    # Conservative abstention:
    #
    # Low probability OR small separation between
    # the top two predictions -> human review.
    abstain = (
        top_prob < 0.55
        or margin < 0.10
    )

    return {
        "top_predictions": [
            {
                "category": str(label),
                "probability": float(prob),
            }
            for label, prob in top
        ],
        "predicted_category": (
            None
            if abstain
            else str(top[0][0])
        ),
        "model_probability": top_prob,
        "margin": margin,
        "needs_human_review": bool(abstain),
        "decision": (
            "Review required before relying on classification"
            if abstain
            else "Classification available; human review still recommended"
        ),
    }


# ============================================================
# CONTRACT ANALYSIS
# ============================================================

def analyze_contract_bytes(
    data: bytes,
    filename: str,
):

    class Upload:

        def __init__(
            self,
            name,
            raw,
        ):
            self.name = name
            self._raw = raw

        def read(self):
            return self._raw

    # --------------------------------------------------------
    # Extract document text
    # --------------------------------------------------------

    text = extract_text(
        Upload(
            filename,
            data,
        )
    )

    if not text.strip():
        raise ValueError(
            "No readable text was extracted from the document"
        )

    # --------------------------------------------------------
    # Segment into clause/section blocks
    # --------------------------------------------------------

    clauses = segment_clauses(text)

    if not clauses:
        raise ValueError(
            "No sufficiently long clause/section blocks "
            "were detected"
        )

    # --------------------------------------------------------
    # Classify each clause
    # --------------------------------------------------------

    results = []

    for number, clause_text in enumerate(
        clauses,
        1,
    ):

        result = classify(
            clause_text
        )

        # ----------------------------------------------------
        # Evidence-based risk detection
        # ----------------------------------------------------

        flags = detect_flags(
            clause_text,
            result["predicted_category"],
        )

        results.append(
            {
                "number": number,
                "text": clause_text,
                "result": result,
                "risks": flags,
            }
        )

    return {
        "text_length": len(text),
        "clauses": results,
    }

