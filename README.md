# Harvey - Discord Bot

Simple Discord bot for the Collectez community.

## Features
- Ping the current status of Collectez's Teztools node.
- Steal emojis from image sources and add them to the current server.
- Add or remove roles by emoji reaction. Reaction roles are managed with a Sqlite3 database.

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

----

## To be implemented:
- Randomly selected message thumbnails for commands with Embed returns.
- Follow Twitter accounts and output a feed of tweets based on requested keywords.
- Monitor blockchain transactions and post notifications based on contract ID and transaction amount.
- Set and manage recurring function calls.
- Create and manage giveaways.
- Spin up temporary nodes on a given RPS.
- Other features TBD.
