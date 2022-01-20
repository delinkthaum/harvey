""" tez.py -- Tezos methods for Harvey.

    Language: Python 3.9

    Powered by TzKT API: tzkt.io

    NOTE: Code methods and inspiration yoinked from the following:
    - https://github.com/murbard/pytezos
"""

from dataclasses import dataclass
from typing import Tuple, List, Union
import logging
import re

import pandas as pd
import requests

from harvey import config
from harvey.utils.exceptions import TezosError

PUBLIC_NODES = {
    "mainnet": [
        "http://localhost:8732/",
        "https://rpc.tezrpc.me/",
        "https://mainnet-node.tzscan.io/",
    ],
    "zeronet": ["http://localhost:8732/", "https://zeronet-node.tzscan.io/"],
    "alphanet": ["http://localhost:8732/", "https://alphanet-node.tzscan.io/"],
}
TZKT_BASE_URL = "https://api.tzkt.io/v1"
FXHASH_GENTK = "KT1KEa8z6vWXDJrVqtMrAeDVzsvxat3kHaCE"
FXHASH_MARKETPLACE = "KT1Xo5B7PNBAeynZPmca4bRh6LQow4og1Zb9"


@dataclass
class FxhashSale(object):
    """Dataclass containing info about an fxhash sale.

    Attributes:
    ----------
    token_id: int
        Numeric ID of the token. Used to create a fxhash link to the token.
    amount: float
        Sale amount in Tez.
    seller_hash: str
        Seller of the token. Used to create a profile link.
    seller_alias: str
        Fxhash alias of the seller. Used to provide a readable name. If no alias exists,
        the seller's hash is used.
    buyer_hash: str
        Buyer of the token. Used to create a profile link.
    buyer_alias: str
        Fxhash alias of the buyer. Used to provide a readable name. If no alias exists,
        the buyer's hash is used.
    timestamp: str
        Date and time of the sale. Stored as a timestamp value pulled from the sale
        operation RPC data.
    token_ipfs: str
        Token ipfs link. Used to attach the image to the Embed.
    token_title: str
        Title of the token. Used for the message header.
    token_author: str
        Creator of the token. Used for the message header.
    txn_hash: str
        Sale operation. Used to create a TzKT link to the sale.
    """

    token_id: int = None
    amount: float = 0.0
    seller_hash: str = None
    seller_alias: str = None
    buyer_hash: str = None
    buyer_alias: str = None
    timestamp: str = None
    token_ipfs: str = None
    token_title: str = None
    token_author: str = None
    txn_hash: str = None


class TezosConnection(object):
    """Connection to the Tezos blockchain through a node."""

    def __init__(self, uri: str = config.NODE_RPC):
        """Initialize connection methods to the Tezos blockchain.

        Parameters
        ----------
        uri: str
            Node address to use. Any of the above PUBLIC_NODES addresses can be used if
            desired.
            (Optional) Defaults to: config.NODE_RPC
        """
        self.uri = uri
        self.session = requests.Session()

    def request(self, method: str, url: str, **kwargs) -> dict:
        """Submit a request to self.session. URL and method parameters are required.
        Additional **kwargs for requests methods are accepted.

        NOTE: This call requires that the site endpoint return a jsonifiable response.
        Use a manual requests module call if this is not the case.

        Parameters
        ----------
        method: str
            Request method to use.
        path: str
            URL to query.

        Returns
        ----------
        dict
            JSON result if a status 200 code is returned by the call. A TezosError is
            raised if another code is returned by the call.
        """
        logging.debug(f"Submitting '{method}' call to '{url}'.")
        result = self.session.request(
            method=method,
            url=url,
            headers={"content-type": "application/json"},  # Standard.
            **kwargs,
        )
        result_code = result.status_code
        if result_code != 200:
            emsg = f"'{method}' call failed with status '{result_code}': {result}."
            logging.error(emsg)
            raise TezosError(emsg)
        else:
            logging.info(f"'{method}' call to '{url}' returned success code 200.")
            return result.json()

    def get(self, url: str, params: dict = None) -> dict:
        """Wrapper over self.request for GET calls.

        Parameters
        ----------
        url: str
            URL to query.
        params: dict
            Requests parameters to pass in to the call.
            (Optional) Defaults to: None

        Returns
        ----------
        dict
            Result of self.request() call.
        """
        # Logging is handled in self.request()
        result = self.request(method="GET", url=url, params=params)
        return result

    def post(self, url: str, params: dict = None) -> dict:
        """Wrapper over self.request for POST calls.

        Parameters
        ----------
        url: str
            URL to query.
        params: dict
            Requests parameters to pass in to the call.
            (Optional) Defaults to: None

        Returns
        ----------
        dict
            Result of self.request() call.
        """
        result = self.request(method="POST", url=url, params=params)
        return result

    def get_current_block(self) -> Tuple[int, str]:
        """Pull the level and hash of the current block.

        Returns
        ---------
        Tuple[int, str]
            [0] int
                Block level.
            [1] str
                Block hash.
        """
        logging.debug("Pulling current block info.")
        url = f"{self.uri}/chains/main/blocks/head/header"
        info = self.get(url=url)
        block_level = info.get("level", None)
        block_hash = info.get("hash", None)
        if not block_level or not block_hash:
            raise TezosError(
                f"Unable to pull info for current block: found hash '{block_hash}' and "
                f"level '{block_level}'."
            )
        else:
            return block_level, block_hash

    def get_block(self, block_id: Union[int, str]) -> dict:
        """Pull the current block's operations.

        Parameters
        ----------
        block_id: Union[int, str]
            Block hash or level to pull.

        Returns
        ---------
        dict
            JSON result of the request call.
        """
        logging.debug(f"Pulling block '{block_id}'.")
        url = f"{self.uri}/chains/main/blocks/{block_id}"
        result = self.get(url=url)
        return result

    def get_transactions_by_block(self, block_id: Union[int, str]) -> pd.DataFrame:
        """Pull the operations in a given block.

        Parameters
        ----------
        block_id: Union[int, str]
            Block hash or level to pull.

        Returns
        ---------
        pd.DataFrame
            JSON transaction data converted to a frame.
        """
        logging.debug(f"Pulling transactiosn in block '{block_id}'.")
        url = f"{self.uri}/chains/main/blocks/{block_id}/operations"
        result = self.get(url=url)
        df = pd.json_normalize(result)
        logging.info(f"Pulled {len(df)} transactions in block '{block_id}'.")
        return df

    def tzkt_get_account(self, address: str) -> dict:
        """Pull an account from the TzKT API.

        Ref.: https://api.tzkt.io/#operation/Accounts_GetByAddress

        Parameters
        ----------
        address: str
            Account address.

        Returns
        ---------
        dict
            JSON result of the request call.
        """
        logging.debug(f"Pulling account info for '{address}' from tzkt.")
        url = f"{TZKT_BASE_URL}/accounts/{address}"
        result = self.get(url=url)
        return result

    def tzkt_get_current_block(self) -> Tuple[int, str]:
        """TzKT API equivalent of self.get_current_block().

        Returns
        ---------
        Tuple[int, str]
            [0] int
                Block level.
            [1] str
                Block hash.
        """
        logging.debug("Pulling current block info from TZKT.")
        url = f"{TZKT_BASE_URL}/head"
        info = self.get(url=url)
        block_level = info.get("level", None)
        block_hash = info.get("hash", None)
        if not block_level or not block_hash:
            raise TezosError(
                f"Unable to pull info for current block: found hash '{block_hash}' and "
                f"level '{block_level}'."
            )
        else:
            return block_level, block_hash

    def tzkt_get_block(self, block_id: Union[int, str]) -> dict:
        """TzKT API equivalent of self.get_block().

        Parameters
        ----------
        block_id: Union[int, str]
            Block hash or level to pull.

        Returns
        ---------
        dict
            JSON result of the request call.
        """
        logging.debug(f"Pulling block '{block_id}' from tzkt.")
        url = f"{TZKT_BASE_URL}/blocks/{block_id}"
        result = self.get(url=url)
        return result

    def tzkt_get_transactions_by_block(
        self, block_id: Union[int, str], status: str = "applied"
    ) -> pd.DataFrame:
        """TzKT API equivalent of self.get_transactions_by_block(). Includes optional
        filtering by transaction status.

        Ref.: https://api.tzkt.io/#operation/Operations_GetTransactions

        Parameters
        ----------
        block_id: Union[int, str]
            Block the transactions went through on. Referred to as "level" in many API
            documentation pages.
        status: str
            Status of the transaction.
            (Optional) Defaults to: "applied"

        Returns
        ---------
        pd.DataFrame
            JSON transaction data converted to a frame.
        """
        logging.debug(f"Pulling transactions in block '{block_id}' from TZKT.")
        url = f"{TZKT_BASE_URL}/operations/transactions"
        params = {
            "level": block_id,
            "limit": 10000,  # Max allowed volume - should always exceed block limit.
            "status": status,
        }
        result = self.get(url=url, params=params)
        df = pd.json_normalize(result)
        logging.debug(f"Pulled {len(df)} transactions from txkt in block '{block_id}'.")
        return df

    def tzkt_get_transaction_by_hash(self, txn_hash: str) -> pd.DataFrame:
        """TzKT API extension of self.tzkt_get_transactions_by_block() that pulls data
        for a single operation.

        Ref.: https://api.tzkt.io/#operation/Operations_GetTransactionByHash

        Parameters
        ----------
        txn_hash: str
            Transaction hash to pull.

        Returns
        ---------
        pd.DataFrame
            JSON transaction data converted to a frame.
        """
        logging.debug(f"Pulling transaction '{txn_hash}' from TZKT.")
        url = f"{TZKT_BASE_URL}/operations/transactions/{txn_hash}"
        result = self.get(url=url)
        df = pd.json_normalize(result)
        logging.debug(
            f"Pulled {len(df)} records for transaction '{txn_hash}' from tzkt."
        )
        return df

    def tzkt_get_fxhash_sales_by_block(
        self, block_id: Union[int, str], min_sale_amount: int = 0
    ) -> List[FxhashSale]:
        """Pull operation hashes for fxhash sales in a given block. A fxhash sale
        operation contains one "collect" transaction, one "transfer" transaction, and
        zero or more balance transfer transactions.

        Parameters
        ----------
        block_id: Union[int, str]
            Block the transactions went through on. Referred to as "level" in many API
            documentation pages.
        min_sale_amount: int
            Filter sales to those above a given amount.
            NOTE: This amount is in Tez. The data returned from tzkt uses MuTez.
            (Optional) Defaults to: 0

        Returns
        ---------
        List[FxhashSale]
            Sale data for fxhash sales above the minimum amount on the block.
        """
        logging.debug(f"Pulling fxhash sales in block '{block_id}'.")
        txns = self.tzkt_get_transactions_by_block(block_id=block_id, status="applied")
        # TODO: There has to be a more elegant way to do this.
        sales_hashes = (
            txns.loc[
                (
                    txns["hash"].map(
                        txns.loc[
                            (txns["parameter.entrypoint"] == "collect")
                            & (txns["amount"] >= min_sale_amount * 1000000)
                            & (txns["target.address"] == FXHASH_MARKETPLACE)
                        ]["hash"].value_counts()
                    )
                    == 1
                )
                & (
                    txns["hash"].map(
                        txns.loc[txns["parameter.entrypoint"] == "transfer"][
                            "hash"
                        ].value_counts()
                    )
                    == 1
                )
            ]["hash"]
            .unique()
            .tolist()
        )
        sales = [self.tzkt_get_fxhash_sale(txn_hash=i) for i in sales_hashes]
        logging.debug(f"Found {len(sales)} fxhash sales in block '{block_id}'.")
        return sales

    def tzkt_get_fxhash_sale(self, txn_hash: str) -> FxhashSale:
        """Pull sale info from an fxhash sale operation and construct a FxhashSale data
        class. Each fxhash sale operation contains one "collect" transaction, one
        "transfer" transaction, and zero or more balance transfer transactions.

        Attributes pulled:
        -- token_id - numeric ID reference to the token on fxhash.
        -- amount - sale amount.
        -- seller_hash - seller's wallet hash.
        -- seller_alias - alias of the seller's wallet if one exists.
        -- buyer_hash - buyer's wallet hash.
        -- buyer_alias - alias of the seller's wallet if one exists.
        -- timestamp - date and time of the sale.
        -- txn_hash - operation hash for the sale.

        Parameters
        ----------
        txn_hash: str
            Operation hash.

        Returns
        ---------
        dict
            Attributes listed above.
        """
        logging.debug(f"Pulling fxhash sale '{txn_hash}'.")
        txn = self.tzkt_get_transaction_by_hash(txn_hash=txn_hash)
        try:
            collect = txn.loc[txn["parameter.entrypoint"] == "collect"][:1].squeeze()
            transfer = txn.loc[txn["parameter.entrypoint"] == "transfer"][:1].squeeze()
        except IndexError:
            emsg = (
                f"Unable to pull 'collect' and 'transfer' transactions within sale "
                f"operation '{txn_hash}'."
            )
            logging.critical(emsg)
            raise ValueError(emsg)
        else:
            sale = FxhashSale(txn_hash=txn_hash)

        # Avoid raising errors if the data model has changed or data is missing.
        # TODO: This disappeared without warning - no longer able to pull seller info?
        diffs = next(iter(collect.get("diffs", list())), dict())
        sale.seller_hash = (
            diffs.get("content", dict()).get("value", dict()).get("issuer", None)
        )
        sale.seller_alias = (
            self.fxhash_get_profile_alias(sale.seller_hash)
            if sale.seller_hash
            else None
        )
        sale.buyer_hash = collect.get("sender.address")
        sale.buyer_alias = (
            self.fxhash_get_profile_alias(sale.buyer_hash) if sale.buyer_hash else None
        )
        sale.amount = collect.get("amount", 0) / 1000000  # MuTez -> Tez
        sale.timestamp = collect.get("timestamp", pd.NaT)
        # Token ID is the only element pulled from the "transfer" txn.
        tparams = next(iter(transfer.get("parameter.value", list())), dict())
        sale.token_id = next(iter(tparams.get("txs", list())), dict()).get("token_id")

        logging.info(f"Pulled fxhash sale '{txn_hash}'.")
        return sale

    def fxhash_get_token(self, token_id: Union[int, str]) -> dict:
        """Pull info about a fxhash token by its ID.

        Parameters
        ----------
        token_id: Union[int, str]
            Token identifier. Should be a 6-7 digit number.

        Returns
        ---------
        dict
            Site info for the token. The following attributes are pulled:
            - Token title.
            - Token author.
            - Token ipfs link.
            - Token hash - pulled from the ipfs link.
        """
        logging.debug(f"Pulling fxhash token '{token_id}'.")
        url = f"https://fxhash.xyz/objkt/{token_id}"
        # fxhash site pages don't return jsonifiable output, so self.get cannot be used.
        resp = requests.get(url=url)
        if result_code := resp.status_code != 200:
            emsg = (
                f"Unable to pull fxhash token '{token_id}' - call yielded "
                f"'{result_code}': {resp}."
            )
            logging.error(emsg)
            raise TezosError(emsg)

        text = resp.text
        # TODO: There has to be a better way to do this.
        try:
            token_title = re.findall("<title>([\S\s]*)<\/title>", text)[0]
        except IndexError:
            logging.error(f"Error pulling fxhash title for token '{token_id}'.")
            token_title = None
        else:
            token_title = token_title.replace("fxhash — ", "")
        try:
            token_ipfs = re.findall(
                (
                    '<meta property="og:image" content="'
                    '(https:\/\/gateway[.]fxhash[.]xyz\/ipfs\/\w{32,})"'
                ),
                text,
            )[0]
        except IndexError:
            logging.error(f"Error pulling ipfs link for token '{token_id}'.")
            token_ipfs = None
        try:
            token_hash = token_ipfs.split("ipfs/")[1]
        except AttributeError:
            token_hash = None
        try:
            # Non-greedy search required to grab specific element.
            token_author = re.findall(
                'created by<\/span><span class="\s?">(.*?)<\/span>', text
            )[0]
        except IndexError:
            logging.error(f"Error pulling fxhash author for token '{token_id}'.")
            token_author = None

        token_data = {
            "token_title": token_title,
            "token_author": token_author,
            "token_ipfs": token_ipfs,
            "token_hash": token_hash,
        }
        logging.info(f"Pulled fxhash token '{token_id}'.")
        return token_data

    def fxhash_get_profile_alias(self, profile_hash: str) -> str:
        """Pull a fxhash user's profile alias if one exists.

        Parameters
        ----------
        profile_hash: str
            Full ID hash of their profile.

        Returns
        ---------
        str
            Alias if one exists. If no alias is found, return the full ID hash.
        """
        logging.debug(f"Pulling fxhash user '{profile_hash}'.")
        url = f"https://fxhash.xyz/pkh/{profile_hash}/collection"
        # fxhash site pages don't return jsonifiable output, so self.get cannot be used.
        resp = requests.get(url=url)
        if result_code := resp.status_code != 200:
            emsg = (
                f"Unable to pull fxhash user '{profile_hash}' - call yielded "
                f"'{result_code}': {resp}."
            )
            logging.error(emsg)
            raise TezosError(emsg)

        text = resp.text
        # TODO: Another spaghetti front-end regex solution to clean up.
        try:
            alias = re.findall("<title>fxhash — (.*) profile<\/title>", text)[0]
        except IndexError:
            logging.info(f"Fxhash user '{profile_hash}' does not have an alias.")
            return profile_hash
        else:
            logging.info(f"Fxhash user '{profile_hash}' has alias '{alias}'.")
            return alias
