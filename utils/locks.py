""" locks.py -- asyncio lock management for Harvey.

    Language: Python 3.9
"""

import asyncio


class Locks(object):
    """Lock manager."""

    def __init__(self):
        """Initialize locks."""
        self.locks = {}
        self.main_lock = asyncio.Lock()

    async def get_lock(self, user_id: int) -> asyncio.Lock:
        """Get a lock for the user.

        Parameters
        ----------
        user_id: int
            User ID to lock.

        Returns
        ----------
        asyncio.Lock
            Lock object.
        """
        async with self.main_lock:
            if not user_id in self.locks:
                self.locks[user_id] = asyncio.Lock()
            return self.locks[user_id]


lock_manager = Locks()
