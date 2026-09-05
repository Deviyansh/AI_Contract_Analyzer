import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, f1_score

BASE = Path(__file__).resolve().parents[2]
MODEL = BASE / "model" / "clause_classifier.joblib"
TEST = BASE / "data" / "processed" / "supplemental_external_test.csv"
OUT = BASE / "outputs" / "external_metrics.json"

def main():
    if not MODEL.exists():
        raise FileNotFoundError("Train the model first.")
    if not TEST.exists():
        raise FileNotFoundError("Run scripts/build_dataset.py first.")
    df = pd.read_csv(TEST).dropna(subset=["label","text"])
    model = joblib.load(MODEL)
    pred = model.predict(df["text"])
    result = {
        "dataset": "supplemental legal_docs external holdout",
        "examples": int(len(df)),
        "accuracy": float(accuracy_score(df["label"], pred)),
        "macro_f1": float(f1_score(df["label"], pred, average="macro", labels=sorted(df["label"].unique()), zero_division=0)),
        "weighted_f1": float(f1_score(df["label"], pred, average="weighted", labels=sorted(df["label"].unique()), zero_division=0)),
        "labels": sorted(df["label"].unique().tolist()),
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    (OUT.parent/"external_classification_report.txt").write_text(
        classification_report(df["label"], pred, labels=sorted(df["label"].unique()), zero_division=0), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
if __name__ == "__main__":
    main()
