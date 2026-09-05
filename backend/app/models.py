from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, Float, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    contracts: Mapped[list["Contract"]] = relationship(back_populates="user", cascade="all, delete-orphan")

class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column(Integer)
    file_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(30), default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user: Mapped[User] = relationship(back_populates="contracts")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="contract", cascade="all, delete-orphan")

class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id", ondelete="CASCADE"), index=True)
    model_version: Mapped[str] = mapped_column(String(120), default="tfidf-logreg-v1")
    status: Mapped[str] = mapped_column(String(30), default="complete")
    clause_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    contract: Mapped[Contract] = relationship(back_populates="analyses")
    clauses: Mapped[list["Clause"]] = relationship(back_populates="analysis", cascade="all, delete-orphan")

class Clause(Base):
    __tablename__ = "clauses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), index=True)
    clause_number: Mapped[int] = mapped_column(Integer)
    clause_text: Mapped[str] = mapped_column(Text)
    predicted_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model_probability: Mapped[float] = mapped_column(Float)
    margin: Mapped[float] = mapped_column(Float)
    needs_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    top_predictions: Mapped[list] = mapped_column(JSON)
    analysis: Mapped[Analysis] = relationship(back_populates="clauses")
    risk_findings: Mapped[list["RiskFinding"]] = relationship(back_populates="clause", cascade="all, delete-orphan")

class RiskFinding(Base):
    __tablename__ = "risk_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clause_id: Mapped[int] = mapped_column(ForeignKey("clauses.id", ondelete="CASCADE"), index=True)
    rule_id: Mapped[str] = mapped_column(String(60))
    category: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    clause: Mapped[Clause] = relationship(back_populates="risk_findings")
