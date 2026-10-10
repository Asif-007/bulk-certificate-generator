
from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CertificateInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_name: str = Field(min_length=1, max_length=150)
    issuer: str = Field(min_length=1, max_length=150)
    completion_date: date


class RecipientInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr


class CertificateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certificate: CertificateInfo
    recipients: list[RecipientInput] = Field(
        min_length=1,
        max_length=500,
    )
