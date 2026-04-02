"""NEX Payroll FastAPI application."""
from fastapi import FastAPI

app = FastAPI(title="NEX Payroll")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
