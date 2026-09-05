from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
CUAD = BASE / "data" / "external" / "cuad"

if __name__ == "__main__":
    print("Place the verified CUAD v1 files in:", CUAD)
    print("Expected: CUAD_v1.json, master_clauses.csv, master_clauses.xlsx, full_contract_pdf/, full_contract_txt/, label_group_xlsx/")
