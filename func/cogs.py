""" cogs.py -- Custom cogs added to Harvey.

    Language: Python 3.9
"""

from discord.ext import commands
import discord

from harvey.utils.locks import lock_manager


def setup(bot: commands.Bot):
    """Initialize commands."""
    bot.add_cog(CommandErrorHandler(bot))
    bot.add_cog(Roles(bot))


class CommandErrorHandler(commands.Cog):
    """Custom error handling for commands."""

    def __init__(self, bot: commands.Bot):
        """Initialize error handler."""
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Handle the event raised when invoking a command fails.

        Parameters
        ----------
        ctx: commands.Context
            The context of the command.
        error: commands.CommandError
            The error raised.
        """
        # Don't handle errors for commands that already have a local handler.
        if hasattr(ctx.command, "on_error"):
            return
        # Similarly, if a cog has an overwritten cog_command_error method, exit
        # immediately.
        if cog := ctx.cog:
            if cog._get_overridden_method(cog.cog_command_error) is not None:
                return
        # Ignore Exceptions where no custom handling is required. Dig for the
        # "original" error to determine if a given Exception should be ignored.
        ignored = (commands.CommandNotFound,)
        error = getattr(error, "original", error)
        if isinstance(error, ignored):
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send(f"Command `{ctx.command}` has been disabled.")
        elif isinstance(error, commands.NoPrivateMessage):
            # Attempt to send message to user. Avoid creating cascaded errors.
            try:
                await ctx.author.send(f"Command `{ctx.command}` is disallowed in DMs.")
            except Exception:
                pass
        elif isinstance(error, commands.MissingRequiredArgument):
            missing_arg = str(error).split(" ")[0]
            await ctx.send(
                f"Command `{ctx.command}` requires argument `{missing_arg}`. See "
                f"`!help {ctx.command}` for more info or add the argument and try "
                f"again."
            )
        else:
            message = (
                f"Command `{ctx.command}` failed with `{error.__class__.__name__}`:"
                f"\n```{error}```"
            )
            if len(message) > 2000:
                await ctx.send(
                    f"Command `{ctx.command}` failed with "
                    f"`{error.__class__.__name__}`. Error too large to display."
                )
            else:
                await ctx.send(message)


class Roles(commands.Cog):
    """Custom reaction role handling."""

    def __init__(self, bot: commands.Bot):
        """Initialize reaction role triggers."""
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle a reaction sent to a message.

        Parameters
        ----------
        payload: discord.RawReactionActionEvent
            Event triggered by a user reacting to a post.
        """
        guild_id = payload.guild_id
        guild = self.bot.get_guild(payload.guild_id)
        user_id = payload.user_id
        bot_id = self.bot.user.id
        logging_channel = self.bot.logging_channels.get(guild_id)
        # Confirm existence of the message and emoji in the database table.
        channel_id = payload.channel_id
        channel = self.bot.get_channel(channel_id)
        message_id = payload.message_id
        message = await channel.fetch_message(message_id)
        emoji = payload.emoji
        emoji_id = emoji.id
        # Ignore posts made by non-bot users to avoid spamming error messages. Also
        # don't assign reactions to the bot.
        if message.author.id != bot_id or user_id == bot_id:
            return
        # Ignore posts made by the bot that aren't for reaction roles.
        if message.embeds[0].title != "Reaction Roles":
            return
        post_exists = self.bot.db.post_exists(
            message_id=message_id,
            channel_id=channel_id,
            guild_id=guild_id,
        )
        if not post_exists:
            return await channel.send(
                f"Message '{message_id}' not found in the Reaction Role database table."
            )
        reactions = self.bot.db.get_roles(guild_id=guild_id, emoji_id=emoji_id)
        if reactions.empty:
            return await channel.send(
                f"Emoji {emoji} ({emoji_id}) not found in the Reaction Role database "
                f"table."
            )

        # Multiple roles may be assigned to the same emoji in the future, though this
        # is currently disallowed.
        roles_to_add = reactions["role_id"].values
        member = await guild.fetch_member(user_id)
        async with (await lock_manager.get_lock(user_id=user_id)):
            for role_id in roles_to_add:
                role = guild.get_role(role_id)
                if role is None:
                    await channel.send(f"Role with ID '{role_id}' not found in server.")
                    continue
                else:
                    await member.add_roles(role)
                    # If the logging channel has been set, use it for role addition/
                    # removal notification.
                    message = f"Assigned role `{role}` to user `{member.name}`."
                    if logging_channel:
                        await logging_channel.send(message)
                    else:
                        await channel.send(message)
            return

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionClearEmojiEvent):
        """Handle a reaction removed from a message.

        Parameters
        ----------
        payload: discord.RawReactionClearEmojiEvent
            Event triggered by a user removing a reaction on a post.
        """
        guild_id = payload.guild_id
        guild = self.bot.get_guild(payload.guild_id)
        logging_channel = self.bot.logging_channels.get(guild_id)
        # Confirm existence of the message and emoji in the database table.
        channel_id = payload.channel_id
        channel = self.bot.get_channel(channel_id)
        message_id = payload.message_id
        message = await channel.fetch_message(message_id)
        emoji = payload.emoji
        emoji_id = emoji.id
        # Ignore posts made by non-bot users to avoid spamming error messages.
        if message.author.id != self.bot.user.id:
            return
        # Ignore posts made by the bot that aren't for reaction roles.
        if message.embeds[0].title != "Reaction Roles":
            return
        post_exists = self.bot.db.post_exists(
            message_id=message_id,
            channel_id=channel_id,
            guild_id=guild_id,
        )
        if not post_exists:
            return await channel.send(
                f"Message '{message_id}' not found in the Reaction Role database table."
            )
        reactions = self.bot.db.get_roles(guild_id=guild_id, emoji_id=emoji_id)
        if reactions.empty:
            return await channel.send(
                f"Emoji {emoji} ({emoji_id}) not found in the Reaction Role database "
                f"table."
            )

        # Multiple roles may be assigned to the same emoji in the future, though this
        # is currently disallowed.
        roles_to_add = reactions["role_id"].values
        user_id = payload.user_id
        member = await guild.fetch_member(user_id)
        async with (await lock_manager.get_lock(user_id=user_id)):
            for role_id in roles_to_add:
                role = guild.get_role(role_id)
                if role is None:
                    await channel.send(f"Role with ID '{role_id}' not found in server.")
                    continue
                else:
                    await member.remove_roles(role)
                    message = f"Removed role `{role}` from user `{member.name}`."
                    # If the logging channel has been set, use it for role addition/
                    # removal notification.
                    if logging_channel:
                        await logging_channel.send(message)
                    else:
                        await channel.send(message)
            return
