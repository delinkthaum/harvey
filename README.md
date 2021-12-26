# Harvey - Discord Bot

Simple Discord bot for the Collectez community.

## Features
- Ping the current status of Collectez's Teztools node.
- Steal emojis from image sources and add them to the current server.
- Add or remove roles by emoji reaction. Reaction roles are managed with a Sqlite3 database.

---

## Set Up

### Discord
1. Create an Application from the [Discord Development Portal](https://discord.com/developers/applications).
2. Create a Bot for your application. Name it Harvey.
3. Grab the Token and ID for your bot.
4. Using the URL at the top of `.env.example`, fill in `BOT_ID` with your ID and invite Harvey to a server.


### Environment Variables
5. Copy `.env.example` and save as `.env`.
6. Fill in `BOT_TOKEN` and `BOT_ID` values for your Discord bot.
    - Update the default `BOT_PREFIX` to use something other than `!` if needed.
7. Fill in `NODE_NAME`, `NODE_STATUS_JSON`, and `NODE_STATUS_PAGE` values for your Teztools node.
    - If you are using a different node provider, update the function in `utils.get_node_status` and the `!node` command as needed. You may not need these environment variables.


### Python
8. Run `pip install requirements.txt` to install the necessary Python modules.
9. Run `python bot.py` to launch Harvey.

---

## User Commands
- `!help` provide information about available commands.
    - Accepts optional `command` and `subcommand` parameters to provide info about specific functionality.
- `!steal` add an emoji to the current server from an image source.
    - Accepts `name` and `url` parameters.
    - `name` is the emoji that will be used.
    - `url` must point to a PNG, JPEG, or GIF.
- `!node` pulls the current status of Collectez's private Teztools node.

## Admin Commands
- `!log` sets a logging channel to use for status outputs.
    - `channel` must be a Channel passed in to set this.
- `!rr` manages reaction roles.
    - `!rr add` adds a reaction role for the current server.
        - `emoji` and `role` arguments must be passed in. One role per emoji is allowed.
        - An optional, multi-word `desc` can be included for each reaction role added.
        - The emoji must be a custom emoji in the current server. Default emojis are not supported by Discord.
    - `!rr remove` removes a reaction role from the current server.
        - `emoji` argument must be passed in.
    - `!rr post` creates a new reaction role post.
    - `!rr check` checks for all posts in the current server and removes records for non-existent posts from the database.
- `!role` creates a new pingable role with a given name.
    - A `role_name` argument is required. A multi-word role name is allowed, but using `_` is recommended over ` `.

---

## To Be Implemented:
- Randomly selected message thumbnails for commands with Embed returns.
- Follow Twitter accounts and output a feed of tweets based on requested keywords.
- Monitor blockchain transactions and post notifications based on contract ID and transaction amount.
- Set and manage recurring function calls.
- Create and manage giveaways.
- Spin up temporary nodes on a given RPS.
- Other features TBD.
