# AI Contract Analyzer

AI-assisted contract clause classification and potential risk-indicator detection with a **React-free vanilla HTML/CSS/JavaScript frontend**, **FastAPI backend**, and **PostgreSQL-only application storage**.

## Architecture

```text
HTML/CSS/JavaScript frontend
          │ HTTPS
          ▼
       FastAPI
          │
          ├── Document extraction (PDF/DOCX/TXT)
          ├── Clause segmentation
          ├── TF-IDF + Logistic Regression inference
          └── Evidence-based risk indicators
          │
          ▼
      PostgreSQL
       ├── Users
       ├── Original contract files (BYTEA)
       ├── Analyses
       ├── Clauses
       └── Risk findings
```

PostgreSQL is the sole persistent application datastore. Original uploaded contract bytes are stored in PostgreSQL so prior contracts remain available after application restarts/redeployments. For production use, database size, backups, retention, and encryption requirements should be configured appropriately for the organization's legal/privacy obligations.

## Features

- Account creation and JWT authentication
- Private per-user contract history
- PDF, DOCX, and TXT upload
- Original contract retrieval
- Contract storage in PostgreSQL
- 17-category clause classification baseline
- Top-3 model probabilities
- Uncertainty/abstention for low-confidence or ambiguous predictions
- Potential risk indicators with matched evidence
- Conservative negation handling
- Analysis history with model versioning
- Human-review workflow language throughout the UI

## Current model

The bundled baseline uses TF-IDF unigrams/bigrams with class-balanced Logistic Regression. The project also contains training/evaluation scripts under `ml/scripts/` from the enhanced research pipeline.

The final CUAD integration and retraining should be performed after verifying the exact dataset fields and creating document-level splits. Do not claim legal accuracy or clinical-style certainty from model probabilities.

## CUAD data

Place the full CUAD v1 dataset under:

```text
data/external/cuad/
```

Expected files include `CUAD_v1.json`, `master_clauses.csv`, `master_clauses.xlsx`, `full_contract_pdf/`, `full_contract_txt/`, and `label_group_xlsx/`.

The repository intentionally does not include the full CUAD contract corpus by default. Verify the dataset's license/redistribution terms before committing or redistributing it.

## Run locally — Docker (recommended)

Install Docker Desktop, then from the project root:

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:5500`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

PostgreSQL is available on `localhost:5432`.

## Run locally — without Docker

Create a PostgreSQL database named `contractai`, then set `DATABASE_URL`.

Backend:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Frontend:

```bash
cd frontend
python -m http.server 5500
```

Set `frontend/config.js` to point at the backend if necessary.

## Training / evaluation

The ML research pipeline is intentionally separate from the web application. Before final retraining with CUAD:

1. Inspect CUAD labels and source-document identifiers.
2. Map only semantically defensible labels to the application's taxonomy.
3. Split by source document, not individual clauses.
4. Run grouped cross-validation and per-class metrics.
5. Keep a genuinely external holdout where possible.
6. Save the resulting model with an explicit version.
7. Run smoke tests for negation and low-confidence cases.

Example scripts from the existing pipeline are retained under `ml/scripts/`.

## Legal and privacy notice

This project is an AI-assisted research and decision-support tool. It does **not** provide legal advice, determine enforceability, or replace a qualified legal professional. A model probability is not legal certainty. A missing configured risk indicator does not mean a contract is safe.

Do not upload confidential contracts to a deployment unless you have verified the hosting environment, access controls, retention policy, backups, applicable privacy/security requirements, and organizational authorization.

## Deployment

The included `render.yaml` defines:

- FastAPI Docker web service
- Render PostgreSQL database
- Static HTML/CSS/JavaScript frontend

Before production deployment, set a strong `JWT_SECRET` and configure `ALLOWED_ORIGINS` to the exact frontend origin.

## License

MIT for the application code unless otherwise stated by included third-party datasets or source materials. Dataset licensing must be checked separately before redistribution.

## Project layout

```text
backend/       FastAPI API, authentication, PostgreSQL persistence, ML integration
frontend/      Vanilla HTML/CSS/JavaScript UI
model/         Bundled baseline classifier
ml/            Dataset preparation, grouped evaluation, and retraining scripts
database/      PostgreSQL schema reference
data/          Training assets and external dataset location
```

## Recommended order for the final CUAD model

Do not run production retraining blindly. First verify the exact CUAD columns and labels, then run the dataset builder and inspect its printed label/source counts. The application can run immediately using the bundled baseline model; CUAD integration is a separate, auditable training step.
