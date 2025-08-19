import re

# Company names (e.g. ABC Ltd, XYZ Inc, DEF Co, Abc and Def Co., Ltd.)
COMPANY_NAME = re.compile(
    r"((\b(?:[A-Z][a-zA-Z&]+(?:\s+[A-Z][a-zA-Z&]+|\ &|\sand)*)\s+)+"
    r"(?:(?:Ltd|Limited|Inc|Corporation|Co|Company)[\.,]*\s*)+\b)",
    re.MULTILINE,
)

# Captures names (e.g. John Doe, Jesus H. Christ)
PERSON_NAME = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?)+\b")

# Captures org names (e.g. The ABC Company, The XYZ Corporation)
ORGANIZATION_NAME = re.compile(r"\b(?:the\s+)?(?:[A-Z][a-zA-Z&]+(?:\s+[A-Z][a-zA-Z&]+)*)\n")


def is_person_name(text: str) -> bool:
    return PERSON_NAME.match(text) is not None


def is_company_name(text: str) -> bool:
    return COMPANY_NAME.match(text) is not None


def is_organization_name(text: str) -> bool:
    return ORGANIZATION_NAME.match(text) is not None
