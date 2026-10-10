
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.certificates import OUTPUT_DIR, generate_certificate
from app.database import Base, SessionLocal, engine, get_db
from app.schemas import CertificateRequest
from app.pdf_import import MAX_UPLOAD_SIZE, parse_student_pdf


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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
            {"name": item.name, "email": str(item.email)}
            for item in request.recipients
        ],
    }


@app.post("/import-students-pdf")
async def import_students_pdf(file: UploadFile = File(...)):
    """Parse and validate a student-list PDF without creating a job."""

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=415,
            detail="Upload a PDF file with content type application/pdf.",
        )

    contents = bytearray()
    while chunk := await file.read(1024 * 1024):
        contents.extend(chunk)
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="The uploaded PDF is too large. Maximum size is 10 MB.",
            )

    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="The uploaded file is not a valid PDF.")

    try:
        return parse_student_pdf(bytes(contents))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def process_generation_job(job_id: int) -> None:
    """Generate PDFs and persist each recipient's outcome."""

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
                recipient.status = "failed"
                recipient.file_path = None
                recipient.error_message = (
                    f"{type(exc).__name__}: {exc}"
                )[:1000]
                job.failed_count += 1

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


@app.get("/jobs/{job_id}")
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    job = db.get(models.GenerationJob, job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Generation job not found.",
        )

    processed_count = job.success_count + job.failed_count
    progress = (
        round(processed_count / job.total_count * 100, 2)
        if job.total_count
        else 0.0
    )

    recipients = [
        {
            "recipient_id": recipient.id,
            "name": recipient.name,
            "email": recipient.email,
            "status": recipient.status,
            "error_message": recipient.error_message,
            "certificate_url": (
                f"/jobs/{job.id}/recipients/{recipient.id}/certificate"
                if recipient.status == "succeeded"
                else None
            ),
        }
        for recipient in job.recipients
    ]

    return {
        "job_id": job.id,
        "status": job.status,
        "course_name": job.course_name,
        "issuer": job.issuer,
        "completion_date": job.completion_date,
        "total_count": job.total_count,
        "success_count": job.success_count,
        "failed_count": job.failed_count,
        "processed_count": processed_count,
        "progress_percent": progress,
        "recipients": recipients,
    }


@app.get("/jobs/{job_id}/recipients/{recipient_id}/certificate")
def download_certificate(
    job_id: int,
    recipient_id: int,
    db: Session = Depends(get_db),
):
    recipient = db.scalar(
        select(models.RecipientResult).where(
            models.RecipientResult.id == recipient_id,
            models.RecipientResult.job_id == job_id,
        )
    )

    if recipient is None:
        raise HTTPException(
            status_code=404,
            detail="Recipient result not found for this job.",
        )

    if recipient.status != "succeeded" or not recipient.file_path:
        raise HTTPException(
            status_code=404,
            detail="Certificate is not available.",
        )

    # Resolve and restrict the path to the certificate output directory.
    output_root = OUTPUT_DIR.resolve()
    file_path = Path(recipient.file_path).resolve()

    try:
        file_path.relative_to(output_root)
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail="Certificate file not found.",
        ) from None

    if not file_path.is_file() or file_path.suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=404,
            detail="Certificate file not found.",
        )

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=f"certificate_{recipient.id}.pdf",
    )
