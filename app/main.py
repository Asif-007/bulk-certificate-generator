
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.schemas import CertificateRequest
from app import models  # Registers the models with SQLAlchemy's metadata.


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create missing tables when the application starts.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Bulk Certificate Generator",
    description="API for generating and retrieving bulk certificates.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/validate-request")
def validate_request(request: CertificateRequest):
    return {
        "valid": True,
        "recipient_count": len(request.recipients),
        "certificate": {
            "course_name": request.certificate.course_name,
            "issuer": request.certificate.issuer,
            "completion_date": request.certificate.completion_date,
        },
        "recipients": [
            {
                "name": recipient.name,
                "email": str(recipient.email),
            }
            for recipient in request.recipients
        ],
    }
