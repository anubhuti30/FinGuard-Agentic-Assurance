from fastapi import FastAPI
from decimal import Decimal, InvalidOperation

app = FastAPI(title="FinGuard - Agentic Budget Guard")

@app.get("/")
def home():
    return {
        "project": "FinGuard",
        "status": "online",
        "docs": "/docs"
    }

@app.post("/check-budget")
def check_budget(budget: str, used: str, proposed: str):
    try:
        b, u, p = map(Decimal, (budget, used, proposed))
        if not all(x.is_finite() for x in (b, u, p)):
            raise ValueError()
        if min(b, u, p) < 0:
            raise ValueError()
    except (InvalidOperation, ValueError):
        return {"allowed": False, "reason": "Invalid amount"}

    allowed = u + p <= b
    return {
        "allowed": allowed,
        "budget": str(b),
        "used": str(u),
        "proposed": str(p),
        "allowed_amount": allowed,
        "reason": "Within budget" if allowed else "Budget exceeded"
    }