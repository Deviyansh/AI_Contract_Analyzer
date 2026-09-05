import re
from pathlib import Path
import pandas as pd
BASE = Path(__file__).parent
RAW_CSV = BASE / "data" / "raw" / "all_reshaped_clauses.csv"
SYNTHETIC_CSV = BASE / "data" / "curated_synthetic_clauses.csv"
OUT_CSV = BASE / "data" / "training_clauses.csv"

LABEL_MAP = {
    "Cap on Liability": "Liability",
    "Uncapped Liability": "Liability",
    "Liquidated Damages": "Liability",
    "Termination for Convenience": "Termination",
    "Post-termination Services": "Termination",
    "Governing Law": "Governing Law",
    "Renewal Term": "Auto-Renewal",
    "Notice Period to Terminate Renewal": "Auto-Renewal",
    "Revenue-Profit Sharing": "Payment Terms",
    "Minimum Commitment": "Payment Terms",
    "Price Restrictions": "Payment Terms",
    "Warranty Duration": "Warranty",
    "IP Ownership Assignment": "Intellectual Property",
    "Joint IP Ownership": "Intellectual Property",
    "Non-Transferable License": "Intellectual Property",
    "Irrevocable or Perpetual License": "Intellectual Property",
    "Affiliate License-Licensee": "Intellectual Property",
    "Affiliate License-Licensor": "Intellectual Property",
    "Unlimited/All-You-Can-Eat License": "Intellectual Property",
    "License Grant": "Intellectual Property",
    "Non-Compete": "Non-Compete",
    "No-Solicit of Employees": "Non-Compete",
    "No-Solicit of Customers": "Non-Compete",
    "Competitive Restriction Exception": "Non-Compete",
    "Covenant not to Sue": "Dispute Resolution",
    "Anti-assignment": "Assignment",
    "Audit Rights": "Audit Rights",
    "Exclusivity": "Exclusivity",
    "Change of Control": "Change of Control",
    "Insurance": "Insurance",
}
MAX_PER_LABEL = 100  
MIN_CHARS = 40
MAX_CHARS = 8500

_MOJIBAKE_FIXES = {
    "\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
    "‚Äô": "'", "‚Äú": '"', "‚Äù": '"', "‚Äì": "-", "‚Äî": "-",
    "√©": "e", "√¥": "o",
}

def clean_clause_text(text: str) -> str:
    text = str(text)
    for bad, good in _MOJIBAKE_FIXES.items():
        text = text.replace(bad, good)
    text = re.sub(r"\(Page\s*\d+\)\s*$", "", text).strip()
    text = re.sub(r"\s+", " ", text)
    return text.strip(' "\'')

def main():
    if not RAW_CSV.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {RAW_CSV}. Make sure the extracted "
            f"archive contents are in data/raw/."
        )
    df = pd.read_csv(RAW_CSV)
    df = df.rename(columns={"clause_type": "label", "clause_text": "text"})
    df = df[df["label"].isin(LABEL_MAP)].copy()
    df["label"] = df["label"].map(LABEL_MAP)
    df["text"] = df["text"].apply(clean_clause_text)
    df = df[df["text"].str.len().between(MIN_CHARS, MAX_CHARS)]
    df = df.drop_duplicates(subset=["text"])
    df["_len"] = df["text"].str.len()
    df = (
        df.sort_values("_len")
        .groupby("label", group_keys=False)
        .head(MAX_PER_LABEL)
        .drop(columns="_len")
    )
    cuad_part = df[["label", "text"]]
    synthetic = pd.read_csv(SYNTHETIC_CSV)
    combined = pd.concat([cuad_part, synthetic], ignore_index=True)
    combined = combined.drop_duplicates(subset=["text"])
    combined.to_csv(OUT_CSV, index=False)

    print("Per-label counts in final combined training set:\n")
    print(combined["label"].value_counts().to_string())
    print(f"\nTotal rows: {len(combined)}")
    print(f"Saved to: {OUT_CSV}")
    print("\nNext step: run `python train_model.py` to train on this data.")

if __name__ == "__main__":
    main()