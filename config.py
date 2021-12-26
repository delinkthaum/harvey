""" config.py -- dotenv variables for Harvey.

    Language: Python 3.9
"""

import os
import pathlib

import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).with_name(".env"))

HARVEY_VERSION = "1.0.0"

BOT_ID = os.getenv("BOT_ID")
TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_PREFIX = os.getenv("BOT_PREFIX")

NODE_NAME = os.getenv("NODE_NAME")
NODE_STATUS_JSON = os.getenv("NODE_STATUS_JSON")
NODE_STATUS_PAGE = os.getenv("NODE_STATUS_PAGE")
