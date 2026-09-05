import io
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import create_token, decode_token, hash_password, verify_password
from .database import Base, engine, db_session
from .models import User, Contract, Analysis, Clause, RiskFinding
from .schemas import AuthRequest, AuthResponse, ContractSummary, AnalysisOut, ClauseOut, RiskOut
from .ml import analyze_contract_bytes, MODEL_VERSION

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "15")) * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

app = FastAPI(title="AI Contract Analyzer API", version="2.0.0")
origins = [x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins if origins != ["*"] else ["*"], allow_credentials=origins != ["*"], allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

def current_user(authorization: Annotated[str | None, Header()] = None) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Authentication required")
    user_id = decode_token(authorization.split(" ", 1)[1].strip())
    with db_session() as db:
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(401, "User not found")
        db.expunge(user)
        return user

def get_contract(db: Session, contract_id: int, user_id: int) -> Contract:
    contract = db.scalar(select(Contract).where(Contract.id == contract_id, Contract.user_id == user_id))
    if not contract:
        raise HTTPException(404, "Contract not found")
    return contract

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "AI Contract Analyzer API", "model_version": MODEL_VERSION}

@app.get("/api/v1/model")
def model_info():
    from .ml import get_model_classes
    return {"model_version": MODEL_VERSION, "categories": get_model_classes()}

@app.post("/api/v1/auth/signup", response_model=AuthResponse)
def signup(payload: AuthRequest):
    with db_session() as db:
        existing = db.scalar(select(User).where(User.email == payload.email.lower()))
        if existing:
            raise HTTPException(409, "An account with this email already exists")
        user = User(email=payload.email.lower(), password_hash=hash_password(payload.password))
        db.add(user); db.flush()
        token = create_token(user.id)
        return AuthResponse(access_token=token, email=user.email)

@app.post("/api/v1/auth/login", response_model=AuthResponse)
def login(payload: AuthRequest):
    with db_session() as db:
        user = db.scalar(select(User).where(User.email == payload.email.lower()))
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(401, "Invalid email or password")
        return AuthResponse(access_token=create_token(user.id), email=user.email)

@app.get("/api/v1/contracts", response_model=list[ContractSummary])
def list_contracts(user: User = Depends(current_user)):
    with db_session() as db:
        rows = db.scalars(select(Contract).where(Contract.user_id == user.id).order_by(Contract.created_at.desc())).all()
        return rows

@app.post("/api/v1/contracts", response_model=ContractSummary)
async def upload_contract(file: UploadFile = File(...), user: User = Depends(current_user)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only PDF, DOCX, and TXT files are supported")
    data = await file.read()
    if not data:
        raise HTTPException(400, "The uploaded file is empty")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File exceeds the {MAX_FILE_SIZE // (1024*1024)} MB limit")
    with db_session() as db:
        contract = Contract(user_id=user.id, filename=file.filename, mime_type=file.content_type or "application/octet-stream", file_size=len(data), file_bytes=data, status="uploaded")
        db.add(contract); db.flush()
        return contract

@app.get("/api/v1/contracts/{contract_id}", response_model=ContractSummary)
def get_contract_summary(contract_id: int, user: User = Depends(current_user)):
    with db_session() as db:
        return get_contract(db, contract_id, user.id)

@app.get("/api/v1/contracts/{contract_id}/file")
def download_contract(contract_id: int, user: User = Depends(current_user)):
    with db_session() as db:
        c = get_contract(db, contract_id, user.id)
        return Response(content=c.file_bytes, media_type=c.mime_type, headers={"Content-Disposition": f'inline; filename="{c.filename}"'})

@app.delete("/api/v1/contracts/{contract_id}")
def delete_contract(contract_id: int, user: User = Depends(current_user)):
    with db_session() as db:
        c = get_contract(db, contract_id, user.id)
        db.delete(c)
        return {"status": "deleted"}

@app.post("/api/v1/contracts/{contract_id}/analyze", response_model=AnalysisOut)
def analyze(contract_id: int, user: User = Depends(current_user)):
    with db_session() as db:
        c = get_contract(db, contract_id, user.id)
        try:
            result = analyze_contract_bytes(c.file_bytes, c.filename)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        except Exception as exc:
            raise HTTPException(500, f"Analysis failed: {exc}")
        analysis = Analysis(contract_id=c.id, model_version=MODEL_VERSION, status="complete", clause_count=len(result["clauses"]), review_count=sum(x["result"]["needs_human_review"] for x in result["clauses"]), risk_count=sum(len(x["risks"]) for x in result["clauses"]), completed_at=datetime.utcnow())
        db.add(analysis); db.flush()
        for item in result["clauses"]:
            r = item["result"]
            clause = Clause(analysis_id=analysis.id, clause_number=item["number"], clause_text=item["text"], predicted_category=r["predicted_category"], model_probability=r["model_probability"], margin=r["margin"], needs_human_review=r["needs_human_review"], top_predictions=r["top_predictions"])
            db.add(clause); db.flush()
            for flag in item["risks"]:
                db.add(RiskFinding(clause_id=clause.id, rule_id=flag.rule_id, category=flag.category, severity=flag.severity, evidence=flag.evidence, explanation=flag.explanation))
        db.flush()
        return serialize_analysis(db, analysis.id, user.id)

def serialize_analysis(db: Session, analysis_id: int, user_id: int):
    analysis = db.scalar(select(Analysis).join(Contract).where(Analysis.id == analysis_id, Contract.user_id == user_id))
    if not analysis:
        raise HTTPException(404, "Analysis not found")
    clauses = db.scalars(select(Clause).where(Clause.analysis_id == analysis.id).order_by(Clause.clause_number)).all()
    return AnalysisOut(id=analysis.id, contract_id=analysis.contract_id, model_version=analysis.model_version, status=analysis.status, clause_count=analysis.clause_count, review_count=analysis.review_count, risk_count=analysis.risk_count, created_at=analysis.created_at, completed_at=analysis.completed_at, clauses=[ClauseOut(id=c.id, clause_number=c.clause_number, clause_text=c.clause_text, predicted_category=c.predicted_category, model_probability=c.model_probability, margin=c.margin, needs_human_review=c.needs_human_review, top_predictions=c.top_predictions, risks=[RiskOut(rule_id=r.rule_id, category=r.category, severity=r.severity, evidence=r.evidence, explanation=r.explanation) for r in c.risk_findings]) for c in clauses])

@app.get("/api/v1/contracts/{contract_id}/analysis", response_model=AnalysisOut)
def latest_analysis(contract_id: int, user: User = Depends(current_user)):
    with db_session() as db:
        get_contract(db, contract_id, user.id)
        analysis = db.scalar(select(Analysis).where(Analysis.contract_id == contract_id).order_by(Analysis.created_at.desc()))
        if not analysis:
            raise HTTPException(404, "No analysis exists yet")
        return serialize_analysis(db, analysis.id, user.id)
