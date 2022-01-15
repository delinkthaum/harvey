""" harvey.py -- Discord bot for a Tezos NFT community.

    Language: Python 3.9
"""

import logging
import json
import pathlib

from discord.ext import commands

from func import cogs
from func import commands as orders
from utils import database
from utils import logger
import config

logger.initialize(debug=False)
COMMAND_INFO_FILE = pathlib.Path(__file__).parent.joinpath("json/command_info.json")

bot = commands.Bot(command_prefix=config.DEFAULT_PREFIX, help_command=None)


@bot.event
async def on_ready():
    """Set variables, read in the database, and run command setup."""
    bot.db = database.Database("harvey.db")
    with open(COMMAND_INFO_FILE, "r") as f:
        bot.command_info = json.loads(f.read())

    # Int channel IDs are stored in the database. Channel objects are required for
    # reaction role events.
    bot.logging_channels = {
        guild_id: await bot.fetch_channel(channel_id)
        for guild_id, channel_id in bot.db.get_logging_channels().items()
    }
    bot.sales_feed_active = False

    logging.info(
        f"Logged in as '{bot.user.name}' version {config.HARVEY_VERSION}. "
        f"Latency: {bot.latency * 1000:.2f}ms."
    )
    orders.setup(bot)
    cogs.setup(bot)


try:
    bot.run(config.TOKEN)
except Exception as e:
    logging.critical(
        f"Failed to connect to Discord API - unexpected '{e.__class__.__name__}'."
    )
    exit(1)
