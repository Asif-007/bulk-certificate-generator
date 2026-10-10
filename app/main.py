
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import BackgroundTasks, Depends, FastAPI, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, SessionLocal, engine, get_db
from app.schemas import CertificateRequest
from app import models
from app.certificates import generate_certificate


@asynccontextmanager
async def lifespan(app: FastAPI):
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


def process_generation_job(job_id: int) -> None:
    """Generate certificates and record each recipient's outcome."""

    with SessionLocal() as db:
        job = db.get(models.GenerationJob, job_id)
        if job is None:
            return

        job.status = "processing"
        db.commit()

        recipient_ids = list(
            db.scalars(
                select(models.RecipientResult.id).where(
                    models.RecipientResult.job_id == job_id
                )
            ).all()
        )

        for recipient_id in recipient_ids:
            recipient = db.get(models.RecipientResult, recipient_id)
            if recipient is None:
                continue

            try:
                # Generate the PDF for this recipient.
                file_path = generate_certificate(
                    recipient_name=recipient.name,
                    course_name=job.course_name,
                    issuer=job.issuer,
                    completion_date=job.completion_date,
                )

                recipient.status = "succeeded"
                recipient.file_path = str(file_path)
                recipient.error_message = None
                job.success_count += 1

            except Exception as exc:
                # Record the failure and continue with the next recipient.
                recipient.status = "failed"
                recipient.file_path = None
                recipient.error_message = (
                    f"{type(exc).__name__}: {exc}"
                )[:1000]
                job.failed_count += 1

            # Persist each outcome so progress survives a normal restart
            # after that particular record has been committed.
            db.commit()

        if job.failed_count == 0:
            job.status = "completed"
        elif job.success_count > 0:
            job.status = "partially_failed"
        else:
            job.status = "failed"

        db.commit()


@app.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
def create_generation_job(
    request: CertificateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = models.GenerationJob(
        status="pending",
        course_name=request.certificate.course_name,
        issuer=request.certificate.issuer,
        completion_date=request.certificate.completion_date,
        total_count=len(request.recipients),
        success_count=0,
        failed_count=0,
    )

    db.add(job)
    db.flush()

    for item in request.recipients:
        db.add(
            models.RecipientResult(
                job_id=job.id,
                name=item.name,
                email=str(item.email),
                status="pending",
            )
        )

    db.commit()
    db.refresh(job)

    job_id = job.id
    background_tasks.add_task(process_generation_job, job_id)

    return {
        "job_id": job_id,
        "status": job.status,
        "total_count": job.total_count,
        "message": "Generation job accepted.",
    }
