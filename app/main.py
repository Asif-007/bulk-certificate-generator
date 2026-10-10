
from fastapi import FastAPI

app = FastAPI(
    title="Bulk Certificate Generator",
    description="API for generating and retrieving bulk certificates.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}
