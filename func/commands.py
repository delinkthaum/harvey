""" commands.py -- Commands for Harvey.

    Language: Python 3.9
"""

import asyncio
import logging

from discord.ext import commands
import discord
import pandas as pd
import requests

from harvey import config
from harvey.utils import image_refs  # Not yet implemented.
from harvey.utils import get_node_status
from harvey.utils import tez

# Useful message formatting info:
# https://discord.com/developers/docs/reference#message-formatting-formats


def setup(bot: commands.Bot):
    """Initialize commands."""
    help_command(bot)
    set_logging_channel(bot)
    node(bot)
    steal(bot)
    reaction_roles(bot)
    create_role(bot)
    fxhash_sales_feed(bot)


def help_command(bot: commands.Bot):
    """Tell the user things about commands."""
    bot.remove_command("help")
    # Assume command aliases are unique. Use a map to grab command and subcommand
    # references by alias.
    command_info = bot.command_info
    command_map = {}
    subcommand_map = {}
    for command, info in command_info.items():
        # Start with command name. Include all aliases.
        command_map[command] = command
        for alias in info["aliases"]:
            command_map[alias] = command
        # Then repeat the proces for subcommands.
        for subcommand, subcommand_info in info["subcommands"].items():
            subcommand_map[subcommand] = subcommand
            for sub_alias in subcommand_info["aliases"]:
                subcommand_map[sub_alias] = subcommand

    @bot.command(aliases=["info"])
    async def help(ctx: commands.Context, command: str = None, subcommand: str = None):
        """Provide a high-level overview of all available commands to the user. Or give
        them specific info about a given command and its arguments.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        command: str
            Provide a specific command to get info about. If specified, provide
            specific info about the command's arguments. Otherwise, provide a
            high-level overview of all available commands.
            (Optional) Defaults to None.
        subcommand: str
            Provide a subcommand to get info about. If specified, drill down to the
            subcommand's description, arguments, etc. Otherwise, provide only info
            about the given command.
        """
        if not command:
            logging.debug("High-level help function called.")
            embed = discord.Embed(
                title="Help",
                description="These are the things I can do:",
            )
            for func, info in command_info.items():
                embed.add_field(name=func, value=info["desc"], inline=False)
            embed.set_footer(
                text="Use '!help command' to get info about a specific function."
            )
            return await ctx.send(embed=embed)

        logging.debug(f"Help called for command '{command}'.")
        try:
            command = command_map[command]
            info = command_info[command]
        except KeyError:
            return await ctx.send(f"Command `{command}` does not exist.")
        else:
            title = command
        if subcommand:
            try:
                subcommand = subcommand_map[subcommand]
                info = info["subcommands"][subcommand]
            except KeyError:
                return await ctx.send(
                    f"Command `{command}` does not have subcommand `{subcommand}`."
                )
            else:
                title += f" {subcommand}"

        embed = discord.Embed(title=title, description=info["desc"])
        if aliases := info["aliases"]:
            embed.description += "\n\nAliases:\n" + ", ".join(f"`{i}`" for i in aliases)
        if args := info["args"]:
            embed.description += "\n\nArguments:"
            for arg, arg_desc in args.items():
                embed.description += f"\n`{arg}`: {arg_desc}"
        # Subcommands don't have subcommands.
        try:
            if subcommands := info["subcommands"]:
                embed.description += "\n\nSubcommands:\n" + ", ".join(
                    f"`{i}`" for i in subcommands.keys()
                )
        except KeyError:
            pass
        if footer := info["footer"]:
            embed.set_footer(text=footer)
        return await ctx.send(embed=embed)


def set_logging_channel(bot: commands.Bot):
    """Set the logging channel for specific commands."""
    bot.remove_command("log")

    @bot.command(aliases=["logging"])
    @commands.has_permissions(administrator=True)
    async def log(ctx: commands.Context, channel: discord.TextChannel):
        """Set the logging channel for the current server. If an existing logging
        channel is set, notify the user and override the existing record.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        channel: discord.TextChannel
            Channel to use within the current server.
        """
        guild_id = ctx.guild.id
        if not isinstance(channel, discord.TextChannel):
            raise commands.ArgumentParsingError(
                f"First argument of '{ctx.command}' `channel` must be a channel. "
                f"{type(channel)}:'{channel}' was passed in."
            )
        channel_id = channel.id
        logging.debug(f"Setting logging channel for server '{guild_id}'.")
        if not bot.get_channel(channel_id):
            return await ctx.send(
                f"Failed to swap logging to channel to {channel.mention}. Channel not "
                f"found."
            )

        # The update call creates a new record if one does not already exist.
        success = bot.db.update_logging_channel(
            guild_id=guild_id, channel_id=channel_id
        )
        if not success:
            return await ctx.send(
                f"Failed to swap logging channel to {channel.mention}."
            )
        else:
            bot.logging_channels[guild_id] = channel
            return await ctx.send(
                f"Successfully set logging channel to {channel.mention}."
            )


def node(bot: commands.Bot):
    """Pull node status."""
    bot.remove_command("node")

    @bot.command(aliases=["teztools"])
    async def node(ctx: commands.Context):
        """Pull node status using a simple requests call. Create a message with
        embedded content from node site response.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        """
        node_info = get_node_status.get_node_info(
            status_url=config.NODE_STATUS_JSON, node_name=config.NODE_NAME
        )
        if not node_info:
            node_status = "Error - No Data"
            node_sync = None
            node_disk = None
            node_version = None
            updated = None
            error = True
        else:
            node_status = node_info.get("status", None)
            node_sync = node_info.get("sync_state", None)
            node_disk = node_info.get("diskpct", None)
            node_version = node_info.get("version", None)
            updated = node_info.get("updated", 0)  # Unix timestamp.
            error = False
        embed = discord.Embed(
            title="Node Status", description=f"Status of node {config.NODE_NAME}:"
        )
        embed.add_field(name="Node Status", value=f"`{node_status}`")
        embed.add_field(name="Node Sync", value=f"`{node_sync}`")
        embed.add_field(
            name="Disk Usage", value=f"`{node_disk}{'%' if node_disk else ''}`"
        )
        embed.add_field(name="Node Version", value=f"`{node_version}`")
        embed.add_field(name="Last Updated", value=f"<t:{updated}>")
        embed.add_field(
            name="Status Page",
            value=f"[Teztools System Monitor]({config.NODE_STATUS_PAGE})",
            inline=False,
        )
        if error:
            embed.color = discord.Color.red()
            embed.set_footer(text="Something went wrong!")
        else:
            embed.color = discord.Color.green()
        logging.debug("Posting node status message.")
        return await ctx.send(embed=embed)


def steal(bot: commands.Bot):
    """Steal an emoji."""
    bot.remove_command("steal")

    @bot.command()
    async def steal(ctx: commands.Context, name: str, url: str):
        """Grab an emoji from a URL and add it to the current server with a given name.
        Confirm emoji name and ID to the user in an output message.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        name: str
            Name to use for the emoji. Whitespace characters are disallowed.
        url: str
            Source URL for the emoji image. Must point to a PNG, JPEG, or GIF.
        """
        logging.debug(f"Stealing emoji to '{name}' from page '{url}'.")
        try:
            resp = requests.get(url)
        except Exception as e:
            return await ctx.send(
                f"Unable to grab from URL '{url}': '{e.__class__.__name__}'."
            )
        else:
            if code := resp.status_code != 200:
                logging.error(f"Failed to add emoji - page yields '{code}'.")
                return await ctx.send(f"URL '{url}' yields status code '{code}'.")
        try:
            emoji = await ctx.guild.create_custom_emoji(name=name, image=resp.content)
        except discord.InvalidArgument:
            msg = "Invalid image type. Only PNG, JPEG, and GIF are supported."
            logging.error(msg)
            return await ctx.send(msg)
        else:
            logging.info(f"Stole emoji to '{name}' from page '{url}'.")
            return await ctx.send(
                f"Successfully added emoji `{emoji.name}` with ID `{emoji.id}`."
            )


def reaction_roles(bot: commands.Bot):
    """Create and manage custom reaction roles."""
    bot.remove_command("reaction_roles")

    async def check_posts(
        bot: commands.Bot, posts: pd.DataFrame, guild_id: str
    ) -> dict:
        """Check the existence of Reaction Role posts. If any posts are missing,
        remove them from the database.

        Parameters
        ----------
        bot: commands.Bot
            Discord bot.
        posts: pd.DataFrame
            Result of db.get_posts() call.
        guild_id: str
            Server ID where posts are being checked.

        Returns
        ---------
        dict
            Key-value pairs for existing posts where key is message_id and value is
            post_id.
        """
        logging.debug(
            f"Checking existence for {len(posts)} Reaction Role posts in server "
            f"'{guild_id}'."
        )
        posts_found = {}
        for _, p in posts.iterrows():
            channel_id = p["channel_id"]
            message_id = p["message_id"]
            channel = bot.get_channel(channel_id)
            try:
                _ = await channel.fetch_message(message_id)
            except discord.NotFound:
                logging.info(
                    f"Post '{message_id}' in channel '{channel_id}' no longer exists. "
                    f"Removing from database."
                )
                _ = bot.db.delete_post(
                    message_id=message_id, channel_id=channel_id, guild_id=guild_id
                )
            else:
                logging.debug(f"Post '{message_id}' in channel '{channel_id}' found.")
                posts_found[message_id] = channel_id
        logging.info(
            f"Found {len(posts_found)} Reaction Role posts in server '{guild_id}'."
        )
        return posts_found

    @bot.group(aliases=["rr"])
    @commands.has_permissions(administrator=True)
    async def reaction_roles(ctx: commands.Context):
        if not ctx.invoked_subcommand:
            message = "Command `reaction_roles` has subcommands: " + ", ".join(
                f"`{i}`"
                for i in bot.command_info["reaction_roles"]["subcommands"].keys()
            )
            return await ctx.send(message)

    @reaction_roles.command(aliases=["c"])
    async def check(ctx: commands.Context):
        """Check all reaction role posts in the database. If the post still exists,
        remove it from the database. Then list all active posts.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        """
        guild_id = ctx.guild.id
        logging.debug(f"Initializing reaction roles for server '{guild_id}'.")
        db_posts = bot.db.get_posts(guild_id=guild_id)
        if db_posts.empty:
            return await ctx.send(
                "No Reaction Role posts found. Use `rr post` to create one."
            )
        posts_found = await check_posts(bot=bot, posts=db_posts, guild_id=guild_id)
        embed = discord.Embed(
            title="Active Reaction Role Messages",
            description=(
                "These are the active Reaction Role messages in the current server:"
            ),
        )
        for message_id, channel_id in posts_found.items():
            embed.add_field(name=channel_id, value=message_id, inline=False)
        return await ctx.send(embed=embed)

    @reaction_roles.command(aliases=["p"])
    async def post(ctx: commands.Context):
        """Create a new reaction role post in the current channel. Apply all active
        reaction emoji-role pairs in the server to the post. If any emojis or roles are
        not found, notify the user and don't add them.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        """
        channel_id = ctx.channel.id
        guild_id = ctx.guild.id
        logging.debug(f"Creating new Reaction Role post in channel '{channel_id}'.")

        # Create the base message without reactions to allow for each emoji's existence
        # to be checked. If a DB update error is hit, let it raise to stop the function.
        embed = discord.Embed(
            title="Reaction Roles",
            description=(
                "React to this message with one of the below emojis to be assigned the "
                "corresponding role. To remove a role, un-react.\n\n_ _"
            ),
        )
        embed.set_footer(
            text=(
                "If you can't find the post you used to assign yourself a role, react "
                "and then un-react to remove a role."
            )
        )
        message = await ctx.send(embed=embed)
        message_id = message.id
        _ = bot.db.add_post(
            message_id=message_id, channel_id=channel_id, guild_id=guild_id
        )

        # If any emojis are missing, notify the user and don't add them to the post.
        # Update the post with emoji-role info after successfully cycling through the
        # list.
        role_info = bot.db.get_roles(guild_id=guild_id)
        field_info = {}
        for _, r in role_info.iterrows():
            emoji_id = r["emoji_id"]
            role_id = r["role_id"]
            role_desc = r["role_desc"]
            role = ctx.guild.get_role(role_id)
            if not role:
                await ctx.send(f"Role '{role_id}' not found in server.")
                continue
            try:
                emoji = bot.get_emoji(emoji_id)
                await message.add_reaction(emoji)
            except Exception as e:
                await ctx.send(
                    f"Hit '{e.__class__.__name__}' adding emoji reaction: "
                    f"'{emoji_id}'."
                )
                continue
            else:
                field_info[emoji] = {"id": role_id, "desc": role_desc}
        embed = message.embeds[0]
        for emoji, role_info in field_info.items():
            role_id = role_info["id"]
            if role_desc := role_info["desc"]:
                line = f"\n{emoji} <@&{role_id}> - {role_desc}"
            else:
                line = f"\n{emoji} <@&{role_id}>"
            embed.description += line
        await message.edit(embed=embed)
        logging.info(
            f"Created new Reaction Role post '{message_id}' with {len(field_info)} "
            f"reactions in channel '{channel_id}'."
        )

    @reaction_roles.command(aliases=["a"])
    async def add(
        ctx: commands.Context,
        emoji: discord.Emoji,
        role: discord.Role,
        role_desc: str = None,
        *addtl_desc,
    ):
        """Add a reaction role to all active posts in the current server. If the emoji
        and/or role do not exist in the current server, take no action.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        emoji: discord.Emoji
            Emoji ID to add.
        role: discord.Role
            Corresponding Role for the emoji.
        role_desc: str
            Role name to use. *addtl_desc args may be passed in for a name with
            multiple space-separated words.
            (Optional) Defaults to: None
        """
        guild_id = ctx.guild.id
        if not isinstance(emoji, discord.Emoji):
            raise commands.ArgumentParsingError(
                f"First argument of '{ctx.command}' `emoji` must be an emoji. "
                f"{type(emoji)}:'{emoji}' was passed in."
            )
        else:
            emoji_id = emoji.id
        if not isinstance(role, discord.Role):
            raise commands.ArgumentParsingError(
                f"Second argument of '{ctx.command}' `role` must be a role. "
                f"{type(role)}:'{role}' was passed in."
            )
        else:
            role_id = role.id
        # Discord splits space-separated items as args. A trailing space between words
        # 1 and 2 is thus required for a multi-word role name is passed in.
        if role_desc:
            if addtl_desc:
                role_desc += " "
            role_desc += " ".join(addtl_desc)
        else:
            role_desc = ""  # Avoids 'None' appearing downstream.

        logging.debug(
            f"Adding emoji '{emoji_id}' to role '{role_id}' in server '{guild_id}'. "
            f"Reaction role has description '{role_desc}'."
        )
        # Grab only role IDs.
        server_roles = ctx.guild.roles
        if not role in server_roles:
            return await ctx.send(f"Role `{role}` not found in server.")
        if not emoji.is_usable():
            return await ctx.send(
                f"Emoji {emoji} ({emoji_id}) not found or cannot be accessed by Harvey."
            )
        if not (roles := bot.db.get_roles(guild_id=guild_id, emoji_id=emoji_id)).empty:
            roles = [
                r for r in ctx.guild.roles if r.id in roles["role_id"].values.tolist()
            ]
            return await ctx.send(
                f"Emoji {emoji} ({emoji_id}) is already assigned to role(s) '{roles}'."
            )

        # Once existence has been confirmed, add the reaction role to the database. If
        # no posts are found in the current server, notify the user but don't error.
        _ = bot.db.add_role(
            emoji_id=emoji_id, role_id=role_id, guild_id=guild_id, role_desc=role_desc
        )
        db_posts = bot.db.get_posts(guild_id=guild_id)
        posts_found = await check_posts(bot=bot, posts=db_posts, guild_id=guild_id)
        for message_id, channel_id in posts_found.items():
            channel = bot.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            embed = message.embeds[0]
            if role_desc:
                embed.description += f"\n{emoji} <@&{role_id}> - {role_desc}"
            else:
                embed.description += f"\n{emoji} <@&{role_id}>"
            await message.edit(embed=embed)
            await message.add_reaction(emoji)
            logging.info(
                f"Successfully added reaction role for emoji '{emoji_id}' and role "
                f"'{role_id}' to post '{message_id}'."
            )
        return await ctx.send(
            f"Successfully added emoji {emoji} to Reaction Roles for role `{role}`. "
            f"Updated {len(posts_found)} posts in the current server."
        )

    @reaction_roles.command(aliases=["rem", "r"])
    async def remove(ctx: commands.Context, emoji: discord.Emoji):
        """Cycle through all active Reaction Role posts in the current server and
        remove the given emoji's reaction role(s). If no role is assigned to a post,
        move on to the next one. If the emoji is not found in the database, take no
        action.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        emoji_id: discord.Emoji
            Emoji to remove.
        """
        guild_id = ctx.guild.id
        if not isinstance(emoji, discord.Emoji):
            raise commands.ArgumentParsingError(
                f"First argument of '{ctx.command}' `emoji` must be an emoji. "
                f"{type(emoji)}:'{emoji}' was passed in."
            )
        emoji_id = emoji.id

        logging.debug(
            f"Removing emoji '{emoji}' reaction role(s) in server '{guild_id}'."
        )
        db_roles = bot.db.get_roles(guild_id=guild_id, emoji_id=emoji_id)
        if db_roles.empty:
            return await ctx.send(
                f"Emoji {emoji} ({emoji_id}) is not mapped to any roles in the current "
                f"server."
            )
        db_posts = bot.db.get_posts(guild_id=guild_id)
        posts_found = await check_posts(bot=bot, posts=db_posts, guild_id=guild_id)
        # Handle message removal first - if it fails, db updates shouldn't happen.
        for _, role in db_roles.iterrows():
            role_id = role["role_id"]
            messages_cleared = 0
            for message_id, channel_id in posts_found.items():
                channel = bot.get_channel(channel_id)
                message = await channel.fetch_message(message_id)
                embed = message.embeds[0]
                new_desc = "\n".join(
                    line
                    for line in embed.description.split("\n")
                    if str(emoji_id) not in line
                )
                if new_desc != embed.description:
                    messages_cleared += 1
                embed.description = new_desc
                await message.edit(embed=embed)
                await message.clear_reaction(emoji)
            _ = bot.db.delete_role(
                emoji_id=emoji_id,
                role_id=role_id,
                guild_id=guild_id,
            )
            logging.info(
                f"Successfully removed emoji {emoji} ({emoji_id}) from "
                f"{messages_cleared} and cleared role '{role_id}' from the database."
            )
        return await ctx.send(
            f"Successfully removed emoji {emoji} from Reaction Roles. Updated "
            f"{len(posts_found)} posts in the current server."
        )


def create_role(bot: commands.Bot):
    """Create a new pingable role."""
    bot.remove_command("create_role")

    @bot.command(aliases=["role"])
    @commands.has_permissions(administrator=True)
    async def create_role(ctx: commands.Context, role_name: str, *addtl_name):
        """Create a new pingable role with given name.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        role_name: str
            Role name to use. *addtl_name args may be passed in for a name with
            multiple space-separated words.
        """
        # Discord splits space-separated items as args. A trailing space between words
        # 1 and 2 is thus required for a multi-word role name is passed in.
        if addtl_name:
            role_name += " "
        role_name += " ".join(addtl_name)
        logging.debug(f"Creating new role '{role_name}' in current server.")

        role = await ctx.guild.create_role(
            name=role_name, mentionable=True, reason="Harvey command."
        )
        role_id = role.id
        logging.info(f"Created new role '{role_name}'.")
        return await ctx.send(f"Successfully created new role <@&{role_id}>.")


def fxhash_sales_feed(bot: commands.Bot):
    """Create a live sales feed of objkts on fxhash.xyz"""
    bot.remove_command("fxhash_sales_feed")

    async def create_message(sale: tez.FxhashSale) -> discord.Embed:
        """Create an Embed message for a given fxhash sale operation.

        Parameters
        ----------
        sale: tez.FxhashSale
            Sale data class.

        Returns
        ---------
        discord.Embed
            Message to post to a channel. Includes all token attributes; formatted
            links to the tzkt sale operation, buyer profile, and seller profile; and a
            thumbnail image of the token pulled using the ipfs link.
        """
        # Attributes are organized by use with Embed variables constructed immediately.
        token_id = sale.token_id
        logging.debug(f"Building Embed for fxhash token '{token_id}'.")
        token_title = sale.token_title
        token_author = sale.token_author
        title = f"{token_title} - {token_author}"
        url = f"https://fxhash.xyz/objkt/{token_id}"
        embed = discord.Embed(title=title, url=url)
        # Display the image.
        token_ipfs = sale.token_ipfs
        embed.set_image(url=token_ipfs)
        # Field 1: Sale amount.
        amount = sale.amount
        amount_string = f"{amount}ꜩ"
        embed.add_field(name="Sale Amount", value=amount_string, inline=False)
        # Field 2: Link to the seller's fxhash profile.
        seller_hash = sale.seller_hash
        seller_alias = sale.seller_alias
        seller_string = (
            f"[{seller_alias}](https://www.fxhash.xyz/pkh/{seller_hash}/collection)"
        )
        embed.add_field(name="Seller", value=seller_string, inline=False)
        # Field 3: Link to the buyer's fxhash profile.
        buyer_hash = sale.buyer_hash
        buyer_alias = sale.buyer_alias
        buyer_string = (
            f"[{buyer_alias}](https://www.fxhash.xyz/pkh/{buyer_hash}/collection)"
        )
        embed.add_field(name="Buyer", value=buyer_string, inline=False)
        # Field 4: Link to the sale operation on tzkt.
        txn_hash = sale.txn_hash
        link_string = f"[operation](https://tzkt.io/{txn_hash}) / [ipfs]({token_ipfs})"
        embed.add_field(name="Links", value=link_string, inline=False)

        return embed

    @bot.group(aliases=["sales", "feed"])
    @commands.has_permissions(administrator=True)
    async def fxhash_sales_feed(ctx: commands.Context):
        if not ctx.invoked_subcommand:
            message = "Command `fxhash_sales_feed` has subcommands" + ", ".join(
                f"`{i}`"
                for i in bot.command_info["fxhash_sales_feed"]["subcommands"].keys()
            )
            return await ctx.send(message)

    @fxhash_sales_feed.command(aliases=["status"])
    async def notify(ctx: commands.Context, override_status: str = None):
        """Check the status of the sales feed and provide an update to the user. If
        the optional override_status is provided, instead notify them of the given
        status without checking

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        override_status: str
            Optional status to provide the user - used for start/stop notifications.
            (Optional) Defaults to: None
        """
        # Don't allow the user to spoof statuses by directly calling this command.
        if ctx.command.name == "notify" and override_status:
            raise commands.ArgumentParsingError(
                f"'{ctx.command}' does not accept arguments."
            )
        if not override_status:
            status = "Running" if bot.sales_feed_active else "Inactive"
        else:
            status = override_status
        logging.debug(f"Updating user of sales feed status '{status}'.")
        message = f"Sales feed {status.lower()}. "
        sales_feeds = bot.db.get_sales_feeds()
        if sales_feeds.empty:
            message += (
                "No sales feed channels are set up. Use `!sales add` to set one up."
            )
        else:
            min_sale_amount = min(sales_feeds["minimum_sale_amount"].values)
            message += (
                f"`{len(sales_feeds)}` sales feed channel(s) are currently set up with "
                f"a global minimum amount of `{min_sale_amount}ꜩ`."
            )
        return await ctx.send(message)

    @fxhash_sales_feed.command(aliases=["set", "update"])
    async def add(
        ctx: commands.Context, channel: discord.TextChannel, min_amount: int = 0
    ):
        """Add a sales feed record or update an existing sales feed record for a
        channel in a server.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        channel: discord.TextChannel
            Channel to use within the current server.
        min_amount: int
            Minimum sale amount to post the sale in the channel.
            (Optional) Defaults to: 0, which will include all sales.
        """
        guild_id = ctx.guild.id
        if not isinstance(channel, discord.TextChannel):
            raise commands.ArgumentParsingError(
                f"First argument of '{ctx.command}' `channel` must be a channel. "
                f"{type(channel)}:'{channel}' was passed in."
            )
        channel_id = channel.id
        logging.debug(
            f"Adding sales feed channel '{channel_id}' in server '{guild_id}'."
        )
        # If updating, store original amount for output to user.
        existing_amount = bot.db.get_sales_feed_amount(
            guild_id=guild_id, channel_id=channel_id
        )
        if not bot.db.set_sales_feed(
            guild_id=guild_id, channel_id=channel_id, min_amount=min_amount
        ):
            return await ctx.send(
                f"Unable to add sales feed channel {channel.mention}."
            )
        elif existing_amount:
            return await ctx.send(
                f"Updated sales feed channel {channel.mention} - set min amount from "
                f"`{existing_amount}ꜩ` to `{min_amount}ꜩ`."
            )
        else:
            return await ctx.send(
                f"Added sales feed channel {channel.mention} with min amount "
                f"`{min_amount}ꜩ`."
            )

    @fxhash_sales_feed.command(aliases=["rem", "delete", "del"])
    async def remove(ctx: commands.Context, channel: discord.TextChannel):
        """Remove a sales feed channel in a server.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        channel: discord.TextChannel
            Channel to use within the current server.
        """
        guild_id = ctx.guild.id
        if not isinstance(channel, discord.TextChannel):
            raise commands.ArgumentParsingError(
                f"First argument of '{ctx.command}' `channel` must be a channel. "
                f"{type(channel)}:'{channel}' was passed in."
            )
        channel_id = channel.id
        logging.debug(
            f"Adding sales feed channel '{channel_id}' in server '{guild_id}'."
        )
        existing_amount = bot.db.get_sales_feed_amount(
            guild_id=guild_id, channel_id=channel_id
        )
        if not existing_amount:
            return await ctx.send(
                f"{channel.mention} is not set as a sales feed channel."
            )
        if not bot.db.delete_sales_feed(guild_id=guild_id, channel_id=channel_id):
            return await ctx.send(
                f"Unable to remove sales feed channel {channel.mention}."
            )
        else:
            return await ctx.send(f"Removed sales feed channel {channel.mention}.")

    @fxhash_sales_feed.command(aliases=["list"])
    async def list_channels(ctx: commands.Context):
        """List all active sales feed channels in the current server.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        """
        guild_id = ctx.guild.id
        logging.debug(f"Listing sales feed channels in guild '{guild_id}'.")
        feeds = bot.db.get_sales_feeds()
        in_guild = feeds.loc[feeds["guild_id"] == guild_id]
        sales_channels = []
        for row in in_guild.itertuples():
            channel = await bot.fetch_channel(row.channel_id)
            amount = f"{row.minimum_sale_amount}ꜩ"
            sales_channels.append(f"{channel.mention} - {amount}")
        sales_channels = "\n".join(sales_channels)
        embed = discord.Embed(
            title="Sales Feeds",
            description=(
                f"Below are the sales feed channels in the current server with their "
                f"minimum sale amounts:\n\n_ _{sales_channels}"
            ),
        )
        embed.set_footer(text="Use `!feed add` to add a new sales feed channel.")
        return await ctx.send(embed=embed)

    @fxhash_sales_feed.command(aliases=["begin"])
    @commands.has_permissions(administrator=True)
    async def start(ctx: commands.Context):
        """Start the sales feed and loop through blocks. If it's already active, notify
        the user.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        """
        if bot.sales_feed_active:
            return await ctx.send(
                "Sales feed is already running. Use `sales list` to see active sales "
                "channels in this server. Use `sales add` to add a new channel."
            )
        logging.debug("Initializing sales feed.")
        bot.sales_feed_active = True  # Drives the loop.
        tc = tez.TezosConnection()

        # Keep track of the previous block_id to avoid skipping blocks if multiple
        # messages cause delays over 30s. This also handles delays and other
        # lag/timeout issues.
        prev_block_id = None
        while bot.sales_feed_active:
            current_block_id, _ = tc.tzkt_get_current_block()

            # First time setup and message to user.
            if prev_block_id is None:
                prev_block_id = current_block_id - 1
                status = f"started at block `{current_block_id}`"
                await notify(ctx=ctx, override_status=status)
            # Loop limiters.
            if current_block_id == prev_block_id:  # Block hasn't advanced.
                logging.info(
                    f"Current block '{current_block_id}' has not incremented past "
                    f"'{prev_block_id}'."
                )
                prev_block_id = current_block_id
                # Shorter delay to cycle through blocks if the loop gets behind.
                await asyncio.sleep(20)
                continue
            elif current_block_id > prev_block_id + 1:  # Feed is behind.
                current_block_id = prev_block_id + 1  # Advance one block.
            sales_feeds = bot.db.get_sales_feeds()
            if sales_feeds.empty:
                logging.info(
                    f"No sales feeds active. Skipping block '{current_block_id}'."
                )
                prev_block_id = current_block_id
                await asyncio.sleep(30)  # Full delay until feeds are added.
                continue
            else:
                min_sale_amount = min(sales_feeds["minimum_sale_amount"].values)
                logging.info(
                    f"Searching txns in block '{current_block_id}' for fxhash sales "
                    f"above {min_sale_amount}ꜩ."
                )

            sales = tc.tzkt_get_fxhash_sales_by_block(
                block_id=current_block_id,
                min_sale_amount=min_sale_amount,
            )
            logging.info(
                f"Sales feed found {len(sales)} in block '{current_block_id}' above "
                f"{min_sale_amount}ꜩ."
            )
            # Each sale must be posted to at least one server/channel.
            for sale in sales:
                # Concatenate dicts.
                token_id = sale.token_id
                # TODO: Simplify with update call from dict get_token output?
                fxhash_info = tc.fxhash_get_token(token_id=token_id)
                sale.token_title = fxhash_info["token_title"]
                sale.token_author = fxhash_info["token_author"]
                sale.token_ipfs = fxhash_info["token_ipfs"]
                sale.token_hash = fxhash_info["token_hash"]

                # Construct and post message where appropriate.
                embed = await create_message(sale=sale)
                await asyncio.sleep(0.5)  # Delay to avoid image issues.

                post_channels = sales_feeds.loc[
                    sale.amount >= sales_feeds["minimum_sale_amount"]
                ]
                for row in post_channels.itertuples():
                    guild_id = row.guild_id
                    channel_id = row.channel_id
                    channel = await bot.fetch_channel(channel_id)
                    logging.debug(
                        f"Posting message for {token_id} in channel '{channel_id}' in "
                        f"server '{guild_id}'."
                    )
                    await asyncio.sleep(0.5)  # Delay to avoid image issues.
                    await channel.send(embed=embed)
                    logging.info(
                        f"Posted message for {token_id} in channel '{channel_id}' in "
                        f"server '{guild_id}'."
                    )
                logging.info(
                    f"Posted message for sale of token '{token_id}' to "
                    f"{len(post_channels)} channels."
                )
            logging.info(
                f"Finished posting of {len(sales)} sales for block "
                f"'{current_block_id}'."
            )
            prev_block_id = current_block_id
            # Shorter delay to cycle through blocks if the loop gets behind.
            await asyncio.sleep(20)

    @fxhash_sales_feed.command(aliases=["end"])
    @commands.has_permissions(administrator=True)
    async def stop(ctx: commands.Context):
        """Stop the sales feed by updating bot.sales_feed_active to False. Notify the
        user.

        Parameters
        ----------
        ctx: commands.Context
            Context of the command.
        """
        logging.info(f"Stopping sales feed.")
        bot.sales_feed_active = False
        tc = tez.TezosConnection()
        current_block_id, _ = tc.tzkt_get_current_block()
        status = f"stopped at block `{current_block_id}`"
        return await notify(ctx=ctx, override_status=status)
