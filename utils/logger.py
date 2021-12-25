""" commands.py -- Logger for Harvey. Includes logging of unhandled Exceptions.

    Language: Python 3.9
"""

import logging
import sys
import traceback


def exception_handler(exc_type, exc_value, exc_tb):
    """Handler for exceptino logging."""
    # Remove trailing newlines from the exception message.
    exc = traceback.format_exception(exc_type, exc_value, exc_tb)
    for line in "".join(exc).rstrip().split("\n"):
        logging.critical(line.rstrip())
    # Always raise the error.
    sys.__excepthook__(exc_type, exc_value, exc_tb)


def initialize(debug: bool = False):
    """Initialize a logger. Set sys.excepthook to exception_handler.

    Parameters
    ----------
    debug: bool
        Sets log level. If True, logging.DEBUG is used. Otherwise, logging.INFO is used.
        (Optional) Defaults to: False
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    stream = logging.StreamHandler()
    stream.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(filename)s | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%d %I:%M:%S",
        )
    )
    logger.addHandler(stream)
    sys.excepthook = exception_handler
