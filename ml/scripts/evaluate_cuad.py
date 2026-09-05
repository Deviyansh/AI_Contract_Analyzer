import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, classification_report

BASE=Path(__file__).resolve().parents[2]
MODEL=BASE/"model"/"clause_classifier.joblib"
TEST=BASE/"data"/"processed"/"cuad_external_test.csv"
OUT=BASE/"outputs"/"cuad_external_metrics.json"

def main():
    if not TEST.exists():
        print("CUAD external holdout not present. Run scripts/fetch_cuad.py, then scripts/build_dataset.py.")
        return
    model=joblib.load(MODEL)
    df=pd.read_csv(TEST).dropna(subset=["label","text"])
    pred=model.predict(df["text"])
    labels=sorted(df["label"].unique())
    result={
        "dataset":"CUAD v1 contract-grouped external holdout",
        "examples":int(len(df)),
        "contracts":int(df["group_id"].nunique()),
        "accuracy":float(accuracy_score(df["label"],pred)),
        "macro_f1":float(f1_score(df["label"],pred,labels=labels,average="macro",zero_division=0)),
        "weighted_f1":float(f1_score(df["label"],pred,labels=labels,average="weighted",zero_division=0)),
        "labels":labels,
    }
    OUT.write_text(json.dumps(result,indent=2),encoding="utf-8")
    (OUT.parent/"cuad_external_classification_report.txt").write_text(
        classification_report(df["label"],pred,labels=labels,zero_division=0),encoding="utf-8"
    )
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
