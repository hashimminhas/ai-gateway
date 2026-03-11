DECISION_TASKS = {"invoice_check", "document_review"}

REQUIRED_KEYWORDS = {"amount", "total", "paid", "due", "invoice"}
SUSPICIOUS_KEYWORDS = {"fraud", "unauthorized", "forged", "fake", "illegal"}


def make_decision(task: str, text: str, ai_result: str) -> dict:
    if task not in DECISION_TASKS:
        return None

    combined = (text + " " + ai_result).lower()

    found_required = [kw for kw in REQUIRED_KEYWORDS if kw in combined]
    found_suspicious = [kw for kw in SUSPICIOUS_KEYWORDS if kw in combined]

    if found_suspicious:
        return {
            "decision": "FAIL",
            "reasons": [
                f"Suspicious keyword detected: {kw}"
                for kw in found_suspicious
            ],
            "evidence": found_suspicious,
        }

    if len(found_required) >= 2:
        return {
            "decision": "PASS",
            "reasons": ["Key financial fields present in document"],
            "evidence": found_required,
        }

    return {
        "decision": "NEEDS_INFO",
        "reasons": ["Insufficient financial fields found in document"],
        "evidence": found_required or ["none detected"],
    }
