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
bot.db = database.Database("harvey.db")
with open(COMMAND_INFO_FILE, "r") as f:
    bot.command_info = json.loads(f.read())
bot.logging_channels = {
    guild.id: bot.db.get_logging_channel(guild_id=guild.id) for guild in bot.guilds
}


@bot.event
async def on_ready():
    logging.info(
        f"Logged in as '{bot.user.name}'. Latency: {bot.latency * 1000:.2f}ms."
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
