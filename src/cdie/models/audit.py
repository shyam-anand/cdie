import abc
import datetime
from enum import Enum, auto
from typing import Annotated

from pydantic import AfterValidator, BaseModel


def name_validator(v: str | None) -> str | None:
    if v is None:
        return None
    return v.replace("\n", " ").strip()


class Extracted(abc.ABC, BaseModel):
    confidence: float


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
    issue: str


class Audit(BaseModel):
    auditor: Auditor | None = None
    audit_date: AuditDate | None = None
    suppliers: list[Supplier] = []
    findings: list[Finding] = []
