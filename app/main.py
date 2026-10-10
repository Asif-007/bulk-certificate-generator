
from fastapi import FastAPI

from app.schemas import CertificateRequest

app = FastAPI(
    title="Bulk Certificate Generator",
    description="API for generating and retrieving bulk certificates.",
    version="0.1.0",
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
