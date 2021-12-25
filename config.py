""" config.py -- dotenv variables for Harvey.

    Language: Python 3.9
"""

import os
import pathlib

import dotenv

dotenv.load_dotenv(pathlib.Path(__file__).with_name(".env"))

BOT_ID = os.getenv("BOT_ID")
DEFAULT_PREFIX = os.getenv("BOT_PREFIX")
NODE_NAME = os.getenv("NODE_NAME")
NODE_STATUS_JSON = os.getenv("NODE_STATUS_JSON")
NODE_STATUS_PAGE = os.getenv("NODE_STATUS_PAGE")
TOKEN = os.getenv("BOT_TOKEN")
