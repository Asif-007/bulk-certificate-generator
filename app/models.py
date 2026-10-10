
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )

    course_name: Mapped[str] = mapped_column(String(150), nullable=False)
    issuer: Mapped[str] = mapped_column(String(150), nullable=False)
    completion_date: Mapped[date] = mapped_column(Date, nullable=False)

    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    recipients: Mapped[list["RecipientResult"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )


class RecipientResult(Base):
    __tablename__ = "recipient_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    job_id: Mapped[int] = mapped_column(
        ForeignKey("generation_jobs.id"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )

    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    job: Mapped["GenerationJob"] = relationship(
        back_populates="recipients"
    )
