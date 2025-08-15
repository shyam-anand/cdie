"""Logging configuration.

This module provides centralized logging configuration for the application.
When imported, it automatically configures the root logger with custom formatting
and verbosity control. This configuration affects all loggers in the application,
including those created in submodules using the standard logging module.

Example usage in main application:
    from smaspararboten import loggingconfig  # Import once at application start
    import some_module  # Module can use standard logging

Example usage in submodules:
    import logging
    logger = logging.getLogger(__name__)  # Will inherit root logger configuration

The verbosity level can be controlled using command line arguments:
    -v      : Set logging level to INFO
    -vv     : Set logging level to DEBUG
    (no -v) : Set logging level to WARNING (default)
"""

import logging
from argparse import ArgumentParser
from typing import Optional

# Create a parser instance that can be used by other modules
# We use add_help=False to avoid conflicts with the main application's argument parser
parser = ArgumentParser(add_help=False)
parser.add_argument(
    "-v",
    "--verbose",
    action="count",
    default=0,
    help="Increase verbosity (use -v for INFO, -vv for DEBUG)",
)

LOG_FORMAT = "%(asctime)s %(levelname)s %(module)s::%(funcName)s:%(lineno)d - %(message)s"


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    FORMATS = {
        logging.DEBUG: grey + LOG_FORMAT + reset,
        logging.INFO: grey + LOG_FORMAT + reset,
        logging.WARNING: yellow + LOG_FORMAT + reset,
        logging.ERROR: red + LOG_FORMAT + reset,
        logging.CRITICAL: bold_red + LOG_FORMAT + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def _get_log_level(verbosity: int) -> int:
    """Get the log level based on verbosity count.

    Args:
        verbosity: Number of -v flags (0, 1, or 2)

    Returns:
        The corresponding logging level:
        - 0: WARNING (default)
        - 1: INFO
        - 2: DEBUG
    """

    def get_env_log_level() -> int:
        # if env_log_level := config.get_config("LOG_LEVEL"):
        #     return {
        #         "INFO": 1,
        #         "DEBUG": 2,
        #     }.get(env_log_level, 0)
        return 0

    log_level = verbosity or get_env_log_level()

    return {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }.get(log_level, logging.DEBUG)  # Default to DEBUG if more than 2 -v flags


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger with the specified name.

    This is the recommended way to get a logger in this project.
    It ensures proper configuration and verbosity handling.

    Note: This is just a convenience function. Any logger created with
    logging.getLogger() will work the same way as long as this module
    has been imported somewhere in the application.

    Example:
        from smaspararboten import loggingconfig
        logger = loggingconfig.get_logger(__name__)

    Args:
        name: The name for the logger. If None, the root logger is returned.

    Returns:
        A configured logger instance that inherits settings from the root logger
    """
    return logging.getLogger(name)


# Configure logging automatically when this module is imported
args, _ = parser.parse_known_args()

# Create a formatter with a detailed format string that includes:
# - Timestamp
# - Log level
# - Module name
# - Function name
# - Line number
# - Message

formatter = CustomFormatter()

# Create a handler that writes to stderr
handler = logging.StreamHandler()
handler.setFormatter(formatter)

# Configure the root logger
# This configuration will be inherited by all loggers in the application
root_logger = logging.getLogger()
root_logger.setLevel(_get_log_level(args.verbose))
root_logger.addHandler(handler)

# Prevent propagation to avoid duplicate logs
# This is important because we're configuring the root logger
root_logger.propagate = False

# Log that logging is configured
# This will only be visible if verbosity is set to DEBUG (-vv)
root_logger.debug("Verbosity level set to %s", logging.getLevelName(root_logger.level))

# Log levels for individual modules
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_log_level() -> int:
    """Get the log level for the root logger."""
    return root_logger.level


# Log app configuration before starting the app
logger = get_logger(__name__)
logger.debug("Logging config initialized.")

# Print env variables
# logger.debug(
#     "env: %s",
#     {key: value for key, value in config.list_all().items()},
# )
