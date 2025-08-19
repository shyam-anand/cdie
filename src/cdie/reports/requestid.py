from datetime import datetime


def get_request_id() -> str:
    return datetime.now().strftime("%Y%m%d%H%M%S")
