from cdie import config

RULESETS_DIR = config.RESOURCES_ROOT / "rulesets"


def load_ruleset(filename: str) -> list[str]:
    with open(RULESETS_DIR / filename) as file:
        return [line.rstrip() for line in file]
