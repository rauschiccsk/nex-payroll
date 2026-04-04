from fastapi import FastAPI

app = FastAPI(
    title="NEX Payroll",
    description="Payroll management system",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    """Public. Service health check."""
    return {"status": "healthy"}
