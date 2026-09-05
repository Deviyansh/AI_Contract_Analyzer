from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedGroupKFold, cross_validate
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


# ============================================================
# PATHS
# ============================================================

BASE = Path(__file__).resolve().parents[2]

DATASET = BASE / "data" / "processed" / "augmented_clauses.csv"
CUAD_TEST = BASE / "data" / "processed" / "cuad_external_test.csv"

MODEL_DIR = BASE / "ml" / "artifacts"

MODEL_PATH = MODEL_DIR / "clause_classifier.joblib"
LABELS_PATH = MODEL_DIR / "labels.json"


# ============================================================
# CONFIG
# ============================================================

RANDOM_SEED = 42
N_SPLITS = 5


# ============================================================
# MODEL
# ============================================================

def create_model():

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",

        # Unigrams + bigrams
        ngram_range=(1, 2),

        # Ignore extremely rare terms
        min_df=2,

        # Prevent extremely long vocabulary
        max_features=120000,

        sublinear_tf=True,
    )

    classifier = LogisticRegression(
        max_iter=3000,
        class_weight="balanced",
        solver="liblinear",
        random_state=RANDOM_SEED,
    )

    return Pipeline(
        [
            ("tfidf", vectorizer),
            ("classifier", classifier),
        ]
    )


# ============================================================
# LOAD DATA
# ============================================================

def load_training_data():

    if not DATASET.exists():
        raise FileNotFoundError(
            f"Training dataset not found:\n{DATASET}\n\n"
            "Run build_dataset.py first."
        )

    df = pd.read_csv(DATASET)

    required = {
        "text",
        "label",
        "source",
        "group_id",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Training dataset missing columns: "
            f"{sorted(missing)}"
        )

    df = df.dropna(
        subset=["text", "label", "group_id"]
    ).copy()

    df["text"] = df["text"].astype(str)
    df["label"] = df["label"].astype(str)
    df["group_id"] = df["group_id"].astype(str)

    return df


def load_cuad_test():

    if not CUAD_TEST.exists():
        raise FileNotFoundError(
            f"CUAD test dataset not found:\n{CUAD_TEST}\n\n"
            "Run build_dataset.py first."
        )

    df = pd.read_csv(CUAD_TEST)

    required = {
        "text",
        "label",
        "group_id",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"CUAD test dataset missing columns: "
            f"{sorted(missing)}"
        )

    df = df.dropna(
        subset=["text", "label"]
    ).copy()

    df["text"] = df["text"].astype(str)
    df["label"] = df["label"].astype(str)

    return df


# ============================================================
# GROUPED CROSS VALIDATION
# ============================================================

def evaluate_grouped_cv(df):

    print("\n" + "=" * 70)
    print("5-FOLD GROUPED CROSS-VALIDATION")
    print("=" * 70)

    X = df["text"]
    y = df["label"]
    groups = df["group_id"]

    model = create_model()

    cv = StratifiedGroupKFold(
        n_splits=N_SPLITS,
        shuffle=True,
        random_state=RANDOM_SEED,
    )

    scoring = {
        "accuracy": "accuracy",
        "macro_f1": "f1_macro",
        "weighted_f1": "f1_weighted",
    }

    results = cross_validate(
        model,
        X,
        y,
        groups=groups,
        cv=cv,
        scoring=scoring,
        n_jobs=-1,
        return_train_score=False,
    )

    accuracy = results["test_accuracy"]
    macro_f1 = results["test_macro_f1"]
    weighted_f1 = results["test_weighted_f1"]

    print("\nFold results:")

    for i in range(N_SPLITS):

        print(
            f"Fold {i + 1}: "
            f"accuracy={accuracy[i]:.4f}, "
            f"macro_f1={macro_f1[i]:.4f}, "
            f"weighted_f1={weighted_f1[i]:.4f}"
        )

    print("\nMean:")
    print(
        f"Accuracy:    {accuracy.mean():.4f}"
    )
    print(
        f"Macro F1:    {macro_f1.mean():.4f}"
    )
    print(
        f"Weighted F1: {weighted_f1.mean():.4f}"
    )

    print("\nStd deviation:")
    print(
        f"Accuracy:    {accuracy.std():.4f}"
    )
    print(
        f"Macro F1:    {macro_f1.std():.4f}"
    )
    print(
        f"Weighted F1: {weighted_f1.std():.4f}"
    )

    return {
        "accuracy_mean": float(accuracy.mean()),
        "accuracy_std": float(accuracy.std()),
        "macro_f1_mean": float(macro_f1.mean()),
        "macro_f1_std": float(macro_f1.std()),
        "weighted_f1_mean": float(weighted_f1.mean()),
        "weighted_f1_std": float(weighted_f1.std()),
    }


# ============================================================
# CUAD EXTERNAL TEST
# ============================================================

def evaluate_cuad_test(model, df):

    print("\n" + "=" * 70)
    print("CUAD CONTRACT-LEVEL HOLDOUT TEST")
    print("=" * 70)

    X_test = df["text"]
    y_test = df["label"]

    predictions = model.predict(X_test)

    accuracy = accuracy_score(
        y_test,
        predictions,
    )

    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro",
        zero_division=0,
    )

    weighted_f1 = f1_score(
        y_test,
        predictions,
        average="weighted",
        zero_division=0,
    )

    print(
        f"\nAccuracy:    {accuracy:.4f}"
    )

    print(
        f"Macro F1:    {macro_f1:.4f}"
    )

    print(
        f"Weighted F1: {weighted_f1:.4f}"
    )

    print("\nClassification report:")

    print(
        classification_report(
            y_test,
            predictions,
            zero_division=0,
        )
    )

    labels = sorted(
        set(y_test) | set(predictions)
    )

    cm = confusion_matrix(
        y_test,
        predictions,
        labels=labels,
    )

    cm_df = pd.DataFrame(
        cm,
        index=labels,
        columns=labels,
    )

    print("\nConfusion matrix:")
    print(cm_df.to_string())

    return {
        "accuracy": float(accuracy),
        "macro_f1": float(macro_f1),
        "weighted_f1": float(weighted_f1),
        "labels": labels,
        "confusion_matrix": cm.tolist(),
    }


# ============================================================
# TRAIN FINAL MODEL
# ============================================================

def train_final_model(df):

    print("\n" + "=" * 70)
    print("TRAINING FINAL MODEL")
    print("=" * 70)

    X = df["text"]
    y = df["label"]

    model = create_model()

    model.fit(
        X,
        y,
    )

    return model


# ============================================================
# SAVE MODEL
# ============================================================

def save_model(model, labels):

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    with open(
        LABELS_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            labels,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\nModel saved:")
    print(MODEL_PATH)

    print("\nLabels saved:")
    print(LABELS_PATH)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("AI CONTRACT ANALYZER - MODEL TRAINING")
    print("=" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    train_df = load_training_data()
    cuad_test_df = load_cuad_test()

    print(
        f"\nTraining rows: {len(train_df)}"
    )

    print(
        f"Training groups: "
        f"{train_df['group_id'].nunique()}"
    )

    print(
        f"CUAD test rows: {len(cuad_test_df)}"
    )

    print(
        f"CUAD test groups: "
        f"{cuad_test_df['group_id'].nunique()}"
    )

    # --------------------------------------------------------
    # Dataset summary
    # --------------------------------------------------------

    print("\nTraining sources:")
    print(
        train_df["source"]
        .value_counts()
        .to_string()
    )

    print("\nTraining classes:")
    print(
        train_df["label"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    # --------------------------------------------------------
    # Grouped CV
    # --------------------------------------------------------

    cv_metrics = evaluate_grouped_cv(
        train_df
    )

    # --------------------------------------------------------
    # Final training
    # --------------------------------------------------------

    model = train_final_model(
        train_df
    )

    # --------------------------------------------------------
    # CUAD holdout
    # --------------------------------------------------------

    cuad_metrics = evaluate_cuad_test(
        model,
        cuad_test_df,
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    labels = sorted(
        train_df["label"].unique()
    )

    save_model(
        model,
        labels,
    )

    # --------------------------------------------------------
    # Save metrics
    # --------------------------------------------------------

    metrics = {
        "dataset": {
            "training_rows": int(len(train_df)),
            "training_groups": int(
                train_df["group_id"].nunique()
            ),
            "cuad_test_rows": int(
                len(cuad_test_df)
            ),
            "cuad_test_groups": int(
                cuad_test_df["group_id"].nunique()
            ),
        },
        "grouped_cv": cv_metrics,
        "cuad_holdout": cuad_metrics,
    }

    metrics_path = (
        MODEL_DIR / "training_metrics.json"
    )

    with open(
        metrics_path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            metrics,
            f,
            indent=2,
        )

    print(
        "\nMetrics saved:"
    )

    print(
        metrics_path
    )

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()