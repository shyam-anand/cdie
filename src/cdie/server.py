import argparse

from cdie import config, loggingconfig
import uvicorn.config

logger = loggingconfig.get_logger(__name__)

_default_host = config.get_config("HOST") or "0.0.0.0"
_default_port = int(config.get_config("PORT") or 8005)

parser = argparse.ArgumentParser(description="Småspararboten")
parser.add_argument("-H", "--host", type=str, default=_default_host)
parser.add_argument("-P", "--port", type=int, default=_default_port)


def _log_config():
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = loggingconfig.LOG_FORMAT
    log_config["formatters"]["default"]["fmt"] = loggingconfig.LOG_FORMAT
    log_config["loggers"]["uvicorn"]["level"] = loggingconfig.get_log_level()
    return log_config


def server():
    args, _ = parser.parse_known_args()
    host = args.host or _default_host
    port = args.port or _default_port
    logger.info(f"Starting server on {host}:{port}")

    uvicorn.run(
        "cdie:app",
        host=host,
        port=port,
        log_config=_log_config(),
        log_level=loggingconfig.get_log_level(),
        workers=int(config.get_config("WORKERS") or 1),
    )


if __name__ == "__main__":
    server()
