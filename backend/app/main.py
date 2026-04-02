"""NEX Payroll FastAPI application."""

from fastapi import FastAPI

app = FastAPI(title="NEX Payroll", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
