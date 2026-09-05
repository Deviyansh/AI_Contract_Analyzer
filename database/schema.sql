CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  email VARCHAR(320) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contracts (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  filename VARCHAR(255) NOT NULL,
  mime_type VARCHAR(120) NOT NULL,
  file_size INTEGER NOT NULL,
  file_bytes BYTEA NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_contracts_user_created ON contracts(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS analyses (
  id BIGSERIAL PRIMARY KEY,
  contract_id BIGINT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
  model_version VARCHAR(120) NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'complete',
  clause_count INTEGER NOT NULL DEFAULT 0,
  review_count INTEGER NOT NULL DEFAULT 0,
  risk_count INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_analyses_contract ON analyses(contract_id, created_at DESC);

CREATE TABLE IF NOT EXISTS clauses (
  id BIGSERIAL PRIMARY KEY,
  analysis_id BIGINT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  clause_number INTEGER NOT NULL,
  clause_text TEXT NOT NULL,
  predicted_category VARCHAR(120),
  model_probability DOUBLE PRECISION NOT NULL,
  margin DOUBLE PRECISION NOT NULL,
  needs_human_review BOOLEAN NOT NULL DEFAULT FALSE,
  top_predictions JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_clauses_analysis ON clauses(analysis_id, clause_number);

CREATE TABLE IF NOT EXISTS risk_findings (
  id BIGSERIAL PRIMARY KEY,
  clause_id BIGINT NOT NULL REFERENCES clauses(id) ON DELETE CASCADE,
  rule_id VARCHAR(60) NOT NULL,
  category VARCHAR(120) NOT NULL,
  severity VARCHAR(30) NOT NULL,
  evidence TEXT NOT NULL,
  explanation TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_risk_clause ON risk_findings(clause_id);
