""" database.py -- sqlite storage of relevant functional info for Harvey.

    Language: Python 3.9
"""

from typing import Tuple
import json
import logging
import pathlib
import sqlite3

import pandas as pd

from harvey.utils.exceptions import DatabaseError

MAPPING_FILE = pathlib.Path(__file__).parents[1].joinpath("json/db_tables.json")


class Database(object):
    """Container for bot items."""

    def __init__(self, database: pathlib.Path):
        self.database = pathlib.Path(database)
        if self.database.exists():
            logging.debug(
                f"Initializing database connection to DB file at "
                f"'{self.database.name}'."
            )
        else:
            logging.debug(f"Creating database at DB file '{self.database.name}'.")
        self.rr_role_table = None  # Set for linting.
        self.rr_post_table = None
        self.logging_channel_table = None
        self.sales_feed_table = None
        with open(MAPPING_FILE, "r") as f:
            self.mapping = json.loads(f.read())
        for var, info in self.mapping["tables"].items():
            setattr(self, var, info["name"])
        self.create_tables()

    def get_conn(self) -> Tuple[sqlite3.Connection, sqlite3.Cursor]:
        """Helper function to connect to the internal database.

        Returns
        ----------
        Tuple[sqlite3.Connection, sqlite3.Cursor]
            Connection and cursor objects.
        """
        conn = sqlite3.connect(self.database)
        cursor = conn.cursor()
        return conn, cursor

    def create_tables(self):
        """Create database tables if they don't already exist.

        Parameters
        ----------
        query: str
            Table create query.
        """
        logging.debug("Beginning table instantiation.")
        conn, cursor = self.get_conn()
        for table_type, table_info in self.mapping["tables"].items():
            logging.debug(f"Creating {table_type} table '{table_info['name']}'.")
            cursor.execute(table_info["create_query"])
        conn.commit()
        conn.close()
        logging.info("Completed table instantiation.")

    def role_exists(
        self,
        emoji_id: int,
        role_id: int,
        guild_id: int,
    ) -> bool:
        """Check if a role exists on the self.rr_role_table table.

        Parameters
        ----------
        emoji_id: int
            Emoji ID to check.
        role_id: int
            Role ID to check.
        guild_id: int
            Guild ID to check.

        Returns
        ----------
        bool
            True if role was found. False otherwise.
        """
        query = (
            f"SELECT * FROM '{self.rr_role_table}' WHERE 1=1 AND emoji_id = {emoji_id} "
            f"AND role_id = {role_id} AND guild_id = {guild_id}"
        )
        conn, _ = self.get_conn()
        res = pd.read_sql_query(query, con=conn)
        conn.close()
        return not res.empty

    def add_role(
        self, emoji_id: int, role_id: int, guild_id: int, role_desc: str
    ) -> bool:
        """Add a role to the self.rr_role_table. If the role already exists, raise a
        DatabaseError.

        Parameters
        ----------
        emoji_id: int
            Emoji ID to add.
        role_id: int
            Role ID to add.
        guild_id: int
            Guild ID to add.
        role_desc: str
            Role description.

        Returns
        ---------
        bool
            True if role is added successfully. False or None otherwise.
        """
        logging.debug(
            f"Adding reaction role for emoji '{emoji_id}' and role '{role_id}' and "
            f"description '{role_desc}' in guild '{guild_id}'."
        )
        if self.role_exists(emoji_id=emoji_id, role_id=role_id, guild_id=guild_id):
            raise DatabaseError(
                f"Emoji '{emoji_id}' already belongs to role '{role_id}'."
            )
        # Single quotes ' have to be escaped to avoid conflicts with quote characters.
        role_desc = role_desc.replace("'", "''")
        query = (
            f"INSERT INTO '{self.rr_role_table}' VALUES "
            f"({emoji_id}, {role_id}, {guild_id}, '{role_desc}')"
        )
        conn, cursor = self.get_conn()
        cursor.execute(query)
        conn.commit()
        conn.close()
        if self.role_exists(emoji_id=emoji_id, role_id=role_id, guild_id=guild_id):
            logging.info(
                f"Successfully added reaction role for emoji '{emoji_id}' and role "
                f"'{role_id}' in guild '{guild_id}'."
            )
            return True
        else:
            logging.error(
                f"Unable to add role for emoji '{emoji_id}' and role '{role_id}' in "
                f"guild '{guild_id}'."
            )
            return False

    def delete_role(self, emoji_id: int, role_id: int, guild_id: int) -> bool:
        """Remove a role from the self.rr_role_table. If the role already exists, take
        no action.

        Parameters
        ----------
        emoji_id: int
            Emoji ID to remove.
        role_id: int
            Role ID to remove.
        guild_id: int
            Guild ID to remove.

        Returns
        ---------
        bool
            True if role is removed successfully. False or None otherwise.
        """
        logging.debug(
            f"Removing reaction role for emoji '{emoji_id}' and role '{role_id}' in "
            f"guild '{guild_id}'."
        )
        query = (
            f"DELETE FROM '{self.rr_role_table}' WHERE 1=1 AND emoji_id = {emoji_id} "
            f"AND role_id = {role_id} AND guild_id = {guild_id}"
        )
        conn, cursor = self.get_conn()
        cursor.execute(query)
        conn.commit()
        conn.close()
        if self.role_exists(emoji_id=emoji_id, role_id=role_id, guild_id=guild_id):
            logging.error(
                f"Unable to remove role for emoji '{emoji_id}' and role '{role_id}' in "
                f"guild '{guild_id}'."
            )
            return False
        else:
            logging.info(
                f"Successfully removed reaction role for emoji '{emoji_id}' and role "
                f"'{role_id}' in guild '{guild_id}'."
            )
            return True

    def get_roles(self, guild_id: int, emoji_id: int = None) -> pd.DataFrame:
        """Pull all reaction role info for a given guild. Optionally slice to role(s)
        assigned to a specific emoji.

        Parameters
        ----------
        guild_id: int
            Guild to search.
        emoji_id: int
            Emoji to slice to.
            (Optional) Defaults to: None

        Returns
        ----------
        pd.DataFrame
            Guild info. Contains emoji and role data.
        """
        logging.debug(f"Pulling reaction roles for guild '{guild_id}'.")
        query = (
            f"SELECT * FROM '{self.rr_role_table}' WHERE 1=1 AND guild_id = {guild_id}"
        )
        conn, _ = self.get_conn()
        res = pd.read_sql_query(query, con=conn)
        conn.close()
        if emoji_id:
            res = res.loc[res["emoji_id"] == emoji_id]
            logging.info(
                f"Pulled {len(res)} reaction roles for guild '{guild_id}' assigned to "
                f"emoji '{emoji_id}'."
            )
        else:
            logging.info(f"Pulled {len(res)} reaction roles for guild '{guild_id}'.")
        return res

    def post_exists(
        self,
        message_id: int,
        channel_id: int,
        guild_id: int,
    ) -> bool:
        """Check if a post exists on the self.rr_post_table table.

        Parameters
        ----------
        message_id: int
            Message ID to check.
        channel_id: int
            Channel ID to check.
        guild_id: int
            Guild ID to check.

        Returns
        ----------
        bool
            True if post was found. False otherwise.
        """
        query = (
            f"SELECT * FROM '{self.rr_post_table}' WHERE 1=1 "
            f"AND message_id = {message_id} AND channel_id = {channel_id} "
            f"AND guild_id = {guild_id}"
        )
        conn, _ = self.get_conn()
        res = pd.read_sql_query(query, con=conn)
        conn.close()
        return not res.empty

    def add_post(self, message_id: int, channel_id: int, guild_id: int) -> pd.DataFrame:
        """Add a post to the self.rr_post_table. If the post already exists, take no
        action.

        Parameters
        ----------
        message_id: int
            Message ID to add.
        channel_id: int
            Channel ID to add.
        guild_id: int
            Guild ID to add.

        Returns
        ---------
        bool
            True if post is added successfully. False or None otherwise.
        """
        logging.debug(
            f"Adding reaction role post with ID '{message_id}' in channel "
            f"'{channel_id}' for guild '{guild_id}'."
        )
        if self.post_exists(
            message_id=message_id, channel_id=channel_id, guild_id=guild_id
        ):
            raise DatabaseError(
                f"Post '{message_id}' already found in channel '{channel_id}'."
            )
        query = (
            f"INSERT INTO '{self.rr_post_table}' VALUES "
            f"({message_id}, {channel_id}, {guild_id})"
        )
        conn, cursor = self.get_conn()
        cursor.execute(query)
        conn.commit()
        conn.close()
        if self.post_exists(
            message_id=message_id, channel_id=channel_id, guild_id=guild_id
        ):
            logging.info(
                f"Successfully added reaction role post with ID '{message_id}' in "
                f"channel '{channel_id}' for guild '{guild_id}'."
            )
            return True
        else:
            logging.error(
                f"Unable to add reaction role post with ID '{message_id}' in channel "
                f"'{channel_id}' for guild '{guild_id}'."
            )
            return False

    def delete_post(self, message_id: int, channel_id: int, guild_id: int) -> bool:
        """Remove a post from the self.rr_post_table. If the post does not exist, take
        no action.

        Parameters
        ----------
        message_id: int
            Message ID to remove.
        channel_id: int
            Channel ID to remove.
        guild_id: int
            Guild ID to remove.

        Returns
        ---------
        bool
            True if post is removed successfully. False or None otherwise.
        """
        logging.debug(
            f"Removing reaction role post with ID '{message_id}' in channel "
            f"'{channel_id}' for guild '{guild_id}'."
        )
        query = (
            f"DELETE FROM '{self.rr_post_table}' WHERE 1=1 "
            f"AND message_id = {message_id} AND channel_id = {channel_id} "
            f"AND guild_id = {guild_id} "
        )
        conn, cursor = self.get_conn()
        cursor.execute(query)
        conn.commit()
        conn.close()
        if self.post_exists(
            message_id=message_id, channel_id=channel_id, guild_id=guild_id
        ):
            logging.error(
                f"Unable to remove reaction role post with ID '{message_id}' in "
                f"channel '{channel_id}' for guild '{guild_id}'."
            )
            return False
        else:
            logging.info(
                f"Successfully removed reaction role post with ID '{message_id}' in "
                f"channel '{channel_id}' for guild '{guild_id}'."
            )
            return True

    def get_posts(self, guild_id: int) -> pd.DataFrame:
        """Pull all reaction role posts for a given guild.

        Parameters
        ----------
        guild_id: int
            Guild to search.

        Returns
        ----------
        pd.DataFrame
            Post info. Contains message and channel data.
        """
        logging.debug(f"Pulling reaction roles posts for guild '{guild_id}'.")
        query = (
            f"SELECT * FROM '{self.rr_post_table}' WHERE 1=1 AND guild_id = {guild_id}"
        )
        conn, _ = self.get_conn()
        res = pd.read_sql_query(query, con=conn)
        conn.close()
        logging.info(f"Pulled {len(res)} reaction roles posts for guild '{guild_id}'.")
        return res

    def get_logging_channel(self, guild_id: int) -> int:
        """Pull the current logging channel for a given guild.

        Parameters
        ----------
        guild_id: int
            Guild to search.

        Returns
        ---------
        int
            Channel ID for the logging channel. None if no logging channel is found.
        """
        logging.debug(f"Pulling the logging channel for server '{guild_id}'.")
        query = (
            f"SELECT * FROM '{self.logging_channel_table}' WHERE 1=1 AND "
            f"guild_id = {guild_id}"
        )
        conn, _ = self.get_conn()
        res = pd.read_sql_query(query, con=conn)
        conn.close()
        if res.empty:
            logging.info(f"No logging channel exists for server '{guild_id}'.")
            return None
        else:
            channel_id = res["channel_id"].iloc[0]
            logging.debug(
                f"Found logging channel '{channel_id}' for server '{guild_id}'."
            )
            return channel_id

    def set_logging_channel(self, guild_id: int, channel_id: int) -> bool:
        """Insert a new logging channel record for a given guild.

        Parameters
        ----------
        guild_id: int
            Guild ID to insert.
        channel_id: int
            Channel ID to insert.

        Returns
        ---------
        bool
            True if record is added successfully. False or None otherwise.
        """
        logging.debug(f"Inserting logging channel record for guild '{guild_id}'.")
        query = (
            f"INSERT INTO '{self.logging_channel_table}' VALUES "
            f"({guild_id}, {channel_id})"
        )
        conn, cursor = self.get_conn()
        cursor.execute(query)
        conn.commit()
        conn.close()
        if self.get_logging_channel(guild_id=guild_id):
            logging.info(
                f"Successfully added logging channel '{channel_id}' for server "
                f"'{guild_id}'."
            )
            return True
        else:
            logging.error(f"Unable to add logging channel for server '{guild_id}'.")
            return False

    def update_logging_channel(self, guild_id: int, channel_id: int) -> bool:
        """Update a logging channel record for a given guild with a new channel. If no
        record exists, insert a new record.

        Parameters
        ----------
        guild_id: int
            Guild ID to update.
        channel_id: int
            Channel ID to insert.

        Returns
        ---------
        bool
            True if record is added successfully. False or None otherwise.
        """
        logging.debug(f"Updating logging channel record for guild '{guild_id}'.")
        if not self.get_logging_channel(guild_id=guild_id):
            return self.set_logging_channel(guild_id=guild_id, channel_id=channel_id)
        query = (
            f"UPDATE '{self.logging_channel_table}' SET channel_id={channel_id} "
            f"WHERE 1=1 AND guild_id={guild_id}"
        )
        conn, cursor = self.get_conn()
        cursor.execute(query)
        conn.commit()
        conn.close()
        if self.get_logging_channel(guild_id=guild_id):
            logging.info(
                f"Successfully added logging channel '{channel_id}' for server "
                f"'{guild_id}'."
            )
            return True
        else:
            logging.error(f"Unable to add logging channel for server '{guild_id}'.")
            return False

    def get_logging_channels(self) -> dict:
        """Pull all logging channels from the database. Used to set channels on bot
        initialization.

        Returns
        ---------
        dict
            key-value pairs with format guild_id:channel_id.
        """
        logging.debug("Pulling all logging channels.")
        query = f"SELECT * FROM '{self.logging_channel_table}'"
        conn, _ = self.get_conn()
        res = pd.read_sql_query(query, con=conn)
        conn.close()
        if not res.empty:
            channels = pd.Series(
                res["channel_id"].values, index=res["guild_id"].values
            ).to_dict()
            logging.info(f"Pulled {len(channels)} logging channels saved in database.")
        else:
            channels = {}
            logging.debug("No logging channels saved in database.")
        return channels

    def get_sales_feed_amount(self, guild_id: int, channel_id: int) -> int:
        """Pull the minimum sales amount for a given guild and channel's sales feed.

        Parameters
        ----------
        guild_id: int
            Guild to search.
        channel_id: int
            Channel to search.

        Returns
        ---------
        int
            Minimum sale amount for the sales feed channel. None if no record exists.
        """
        logging.debug(
            f"Pulling the minimum sale amount for server '{guild_id}' and channel "
            f"'{channel_id}'."
        )
        query = (
            f"SELECT * FROM '{self.sales_feed_table}' WHERE 1=1 AND "
            f"guild_id = {guild_id} AND channel_id = {channel_id}"
        )
        conn, _ = self.get_conn()
        res = pd.read_sql_query(query, con=conn)
        conn.close()
        if res.empty:
            logging.info(
                f"No sales feed set for server '{guild_id}' and channel "
                f"'{channel_id}'."
            )
            return None
        else:
            minimum_sale_amount = res["minimum_sale_amount"].iloc[0]
            logging.info(
                f"Found minimum sale feed amount '{minimum_sale_amount}' for server "
                f"'{guild_id}' and channel '{channel_id}'."
            )
            return minimum_sale_amount

    def get_sales_feeds(self) -> pd.DataFrame:
        """Pull all sales feed data in the self.sales_feed_table.

        Returns
        ---------
        pd.DataFrame
            Table data.
        """
        logging.debug(f"Pulling sales feed data from '{self.sales_feed_table}'.")
        query = f"SELECT * FROM '{self.sales_feed_table}'"
        conn, _ = self.get_conn()
        res = pd.read_sql_query(query, con=conn)
        conn.close()
        logging.info(f"Pulled {len(res)} sales feed records.")
        return res

    def set_sales_feed(self, guild_id: int, channel_id: int, min_amount: int) -> bool:
        """Create or update an existing sales feed record in self.sales_feed_table for
        a given server and channel.

        Parameters
        ----------
        guild_id: int
            Guild to set.
        channel_id: int
            Channel to set.
        min_amount: int
            Minimum sale amount - used to filter transactions.

        Returns
        ---------
        bool
            True if record is added successfully. False or None otherwise.
        """
        logging.debug(
            f"Setting sales feed record for server '{guild_id}' and channel "
            f"'{channel_id}' with minimum sale amount '{min_amount}'."
        )
        if not self.get_sales_feed_amount(guild_id=guild_id, channel_id=channel_id):
            query = (
                f"INSERT INTO '{self.sales_feed_table}' VALUES "
                f"({guild_id}, {channel_id}, {min_amount})"
            )
        else:
            query = (
                f"UPDATE '{self.sales_feed_table}' "
                f"SET minimum_sale_amount={min_amount} "
                f"WHERE 1=1 AND guild_id={guild_id} AND channel_id={channel_id}"
            )
        conn, cursor = self.get_conn()
        cursor.execute(query)
        conn.commit()
        conn.close()
        if (
            self.get_sales_feed_amount(guild_id=guild_id, channel_id=channel_id)
            == min_amount
        ):
            logging.info(
                f"Successfully set sales feed record for channel '{channel_id}' in "
                f"server '{guild_id}'."
            )
            return True
        else:
            logging.error(
                f"Unable to set sales feed record for channel '{channel_id}' in "
                f"server '{guild_id}'."
            )
            return False

    def delete_sales_feed(self, guild_id: int, channel_id: int) -> bool:
        """Remove a record from the self.sales_feed_table. If the record does not
        exist, take no action.

        Parameters
        ----------
        guild_id: int
            Guild ID to remove.
        channel_id: int
            Channel ID to remove.

        Returns
        ---------
        bool
            True if record is removed successfully. False or None otherwise.
        """
        logging.debug(
            f"Removing sales feed record for channel '{channel_id}' in guild "
            f"'{guild_id}'."
        )
        query = (
            f"DELETE FROM '{self.sales_feed_table}' WHERE 1=1 "
            f"AND guild_id = {guild_id} AND channel_id = {channel_id} "
        )
        conn, cursor = self.get_conn()
        cursor.execute(query)
        conn.commit()
        conn.close()
        if self.get_sales_feed_amount(
            guild_id=guild_id,
            channel_id=channel_id,
        ):
            logging.error(
                f"Unable to remove sales feed record for channel '{channel_id}' in "
                f"guild '{guild_id}'."
            )
            return False
        else:
            logging.info(
                f"Successfully removed sales feed record for channel '{channel_id}' in "
                f"guild '{guild_id}'."
            )
            return True
