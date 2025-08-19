import abc
import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, field_serializer


def name_validator(v: str | None) -> str | None:
    if v is None:
        return None
    return v.replace("\n", " ").strip()


class Extracted(abc.ABC, BaseModel):
    confidence: float
    context: dict[str, Any] | None = None

    @field_serializer("confidence")
    def serialize_confidence(self, v: float) -> float:
        return round(v, 5)


class Organization(BaseModel):
    name: Annotated[str, AfterValidator(name_validator)]


class Supplier(Extracted):
    organization: Organization
    type: str | None = None


class Auditor(Extracted):
    name: Annotated[str | None, AfterValidator(name_validator)] = None
    organization: Organization | None = None


class AuditDate(Extracted):
    date: datetime.date


class Finding(Extracted):
    id: str
    category: str
    severity: str
    source_method: str
    text: str


class AuditReport(BaseModel):
    auditor: Auditor | None = None
    audit_date: AuditDate | None = None
    suppliers: list[Supplier] = []
    findings: list[Finding] = []
