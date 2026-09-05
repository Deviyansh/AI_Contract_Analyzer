from datetime import datetime
from pydantic import BaseModel, EmailStr, Field

class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: EmailStr

class ContractSummary(BaseModel):
    id: int
    filename: str
    file_size: int
    status: str
    created_at: datetime
    updated_at: datetime

class RiskOut(BaseModel):
    rule_id: str
    category: str
    severity: str
    evidence: str
    explanation: str

class ClauseOut(BaseModel):
    id: int
    clause_number: int
    clause_text: str
    predicted_category: str | None
    model_probability: float
    margin: float
    needs_human_review: bool
    top_predictions: list
    risks: list[RiskOut]

class AnalysisOut(BaseModel):
    id: int
    contract_id: int
    model_version: str
    status: str
    clause_count: int
    review_count: int
    risk_count: int
    created_at: datetime
    completed_at: datetime | None
    clauses: list[ClauseOut]
