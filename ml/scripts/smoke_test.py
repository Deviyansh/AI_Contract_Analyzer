from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from contract_app.predictor import load_model, classify
from contract_app.risk_rules import detect_flags

def main():
    model = load_model()
    cases = [
        "The Contractor shall have unlimited liability for all losses.",
        "The Contractor's liability shall not be unlimited and shall be capped at the fees paid.",
        "Either party may terminate this Agreement upon thirty days written notice.",
    ]
    for text in cases:
        result = classify(model, text)
        flags = detect_flags(text)
        print("\nTEXT:", text)
        print("TOP:", result["top_predictions"])
        print("REVIEW:", result["needs_human_review"])
        print("FLAGS:", [(f.rule_id, f.category, f.severity) for f in flags])
if __name__ == "__main__":
    main()
