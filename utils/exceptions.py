""" exceptions.py -- Custom exceptions for Harvey.

    Language: Python 3.9
"""


class HarveyError(Exception):
    """Base error class."""


class DatabaseError(HarveyError):
    """Container for database-related errors."""


class TezosError(HarveyError):
    """Container for errors related to interacting with the Tezos blockchain."""
