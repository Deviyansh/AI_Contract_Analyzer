from pathlib import Path
import joblib

BASE = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE / "model" / "clause_classifier.joblib"
MIN_PROBABILITY = 0.55
MIN_MARGIN = 0.10

def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Missing model: {MODEL_PATH}. Run `python scripts/train_model.py`.")
    return joblib.load(MODEL_PATH)

def classify(model, text, top_k=3):
    probabilities = model.predict_proba([text])[0]
    classes = model.classes_
    ranked = sorted(zip(classes, probabilities), key=lambda x: x[1], reverse=True)
    top = ranked[:top_k]
    margin = top[0][1] - top[1][1] if len(top) > 1 else top[0][1]
    abstain = top[0][1] < MIN_PROBABILITY or margin < MIN_MARGIN
    return {
        "top_predictions": [{"category": str(label), "probability": float(prob)} for label, prob in top],
        "predicted_category": None if abstain else str(top[0][0]),
        "model_probability": float(top[0][1]),
        "margin": float(margin),
        "needs_human_review": bool(abstain),
        "decision": "Review required before relying on classification" if abstain else "Classification available; human review still recommended",
    }
