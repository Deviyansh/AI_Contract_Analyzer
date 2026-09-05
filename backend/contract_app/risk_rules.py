import re
from dataclasses import dataclass

NEGATIONS = (
    "not", "no", "without", "never", "neither", "nor", "except", "unless",
    "shall not", "will not", "may not", "does not", "do not", "cannot",
)

@dataclass
class RiskFlag:
    rule_id: str
    category: str
    severity: str
    evidence: str
    explanation: str

RULES = [
    ("LIAB-001", "Liability", "High", re.compile(r"\b(?:unlimited|uncapped)\s+liability\b|\bliability\b.{0,50}\b(?:unlimited|uncapped)\b", re.I),
     "Language may indicate an uncapped liability obligation."),
    ("LIAB-002", "Liability", "High", re.compile(r"\bno\s+(?:financial\s+)?cap\b|\bwithout\s+(?:any\s+)?(?:financial\s+)?cap\b", re.I),
     "Language may indicate that no liability cap applies."),
    ("TERM-001", "Termination", "Medium", re.compile(r"\bterminate\b.{0,80}\bwithout\s+(?:prior\s+)?notice\b|\bwithout\s+(?:prior\s+)?notice\b.{0,80}\bterminate\b", re.I),
     "Termination language may permit termination without advance notice."),
    ("TERM-002", "Termination", "Medium", re.compile(r"\bterminate\b.{0,80}\bwithout\s+(?:cause|reason)\b|\bwithout\s+(?:cause|reason)\b.{0,80}\bterminate\b", re.I),
     "Termination without cause may materially affect contractual stability."),
    ("INDEM-001", "Indemnification", "High", re.compile(r"\bunlimited\b.{0,60}\bindemnif\w*|\bindemnif\w*.{0,60}\bunlimited\b", re.I),
     "Indemnification language may be uncapped."),
    ("PAY-001", "Payment Terms", "Medium", re.compile(r"\bnon[-\s]refundable\b|\bnon[-\s]cancel(?:l)?able\b", re.I),
     "Payment may be non-refundable or non-cancellable."),
    ("PAY-002", "Payment Terms", "Low", re.compile(r"\blate\s+fee\b|\binterest\b.{0,40}\b(?:late|overdue)\b", re.I),
     "Late-payment charges or interest may apply."),
    ("RENEW-001", "Auto-Renewal", "Medium", re.compile(r"\bautomatically\s+renew\b|\bauto[-\s]?renew(?:al)?\b", re.I),
     "Automatic renewal language is present; review notice and opt-out terms."),
    ("WARR-001", "Warranty", "Medium", re.compile(r"\bas[-\s]?is\b", re.I),
     "An 'as-is' provision may limit warranty protection."),
    ("WARR-002", "Warranty", "Medium", re.compile(r"\bdisclaims?\s+(?:all\s+)?warrant(?:y|ies)\b", re.I),
     "Warranty disclaimers are present."),
    ("IP-001", "Intellectual Property", "Medium", re.compile(r"\b(?:irrevocable|perpetual)\b.{0,80}\blicen[cs]", re.I),
     "A perpetual or irrevocable license may create a broad continuing right."),
    ("IP-002", "Intellectual Property", "Medium", re.compile(r"\bexclusive\b.{0,80}\blicen[cs]|\blicen[cs].{0,80}\bexclusive\b", re.I),
     "An exclusive license may materially restrict the licensor."),
    ("NC-001", "Non-Compete", "Medium", re.compile(r"\b(?:worldwide|anywhere\s+in\s+the\s+world)\b", re.I),
     "A worldwide geographic scope may be unusually broad depending on context."),
    ("DISP-001", "Dispute Resolution", "Medium", re.compile(r"\bwaiv(?:e|er).{0,60}\bjury\s+trial\b|\bjury\s+trial\b.{0,60}\bwaiv(?:e|er)", re.I),
     "The clause may waive a jury-trial right."),
    ("DISP-002", "Dispute Resolution", "Medium", re.compile(r"\bclass\s+action\b.{0,60}\bwaiv|\bwaiv.{0,60}\bclass\s+action\b", re.I),
     "The clause may waive participation in a class action."),
    ("EXCL-001", "Exclusivity", "Medium", re.compile(r"\bsole\s+and\s+exclusive\b|\bexclusively\b", re.I),
     "Exclusive-dealing language is present; review scope and duration."),
    ("ASSIGN-001", "Assignment", "Medium", re.compile(r"\bassign(?:ment)?\b.{0,100}\bwithout\b.{0,50}\bconsent\b", re.I),
     "Assignment restrictions are present; review who controls consent."),
    ("CHANGE-001", "Change of Control", "Medium", re.compile(r"\bchange\s+of\s+control\b.{0,100}\bterminate\b|\bterminate\b.{0,100}\bchange\s+of\s+control\b", re.I),
     "Change-of-control language may trigger termination or other consequences."),
]

def _is_negated(text, start, end):
    local = re.sub(r"\s+", " ", text[max(0, start-100):min(len(text), end+40)]).lower()
    # Conservative phrase-level negation for common high-risk triggers.
    blocked = (
        r"\bnot\s+(?:be\s+)?(?:unlimited|uncapped)\b",
        r"\bnot\s+automatically\s+renew\b",
        r"\bnot\s+non[-\s]refundable\b",
        r"\bnot\s+non[-\s]cancel(?:l)?able\b",
        r"\bnot\s+exclusive(?:ly)?\b",
        r"\bnot\s+worldwide\b",
        r"\bnot\s+as[-\s]?is\b",
        r"\bdoes\s+not\s+disclaim\b",
        r"\bdo\s+not\s+disclaim\b",
    )
    return any(re.search(pattern, local) for pattern in blocked)

def detect_flags(text, predicted_category=None):
    flags=[]
    for rule_id, category, severity, pattern, explanation in RULES:
        if predicted_category and category != predicted_category:
            continue
        for m in pattern.finditer(text):
            if _is_negated(text, m.start(), m.end()):
                continue
            start=max(0,m.start()-90); end=min(len(text),m.end()+120)
            evidence=re.sub(r"\s+"," ",text[start:end]).strip()
            flags.append(RiskFlag(rule_id,category,severity,evidence,explanation))
            break
    return flags

def summarize_risk(flags):
    if any(f.severity=="High" for f in flags): return "Review required"
    if any(f.severity=="Medium" for f in flags): return "Review recommended"
    if flags: return "Minor indicator"
    return "No configured indicator"
