from cdie import config

KEYWORDS_DIR = config.RESOURCES_ROOT / "keywords"


def load_keywords(filename: str) -> list[str]:
    """
    Loads keywords from textfiles in resources/keywords
    """
    with open(KEYWORDS_DIR / filename) as file:
        return [line.rstrip() for line in file]
