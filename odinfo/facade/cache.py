"""
Cross-process cache for the ODInfo facade.

Uses file-based invalidation to coordinate cache clearing across multiple
worker processes. Each worker maintains its own in-memory cache but checks
a shared invalidation file to know when to clear it.
"""

import logging
import os
import time
from pathlib import Path

from odinfo.config import INSTANCE_DIR, executable_path

logger = logging.getLogger('od-info.cache')

INVALIDATION_FILE = Path(executable_path(INSTANCE_DIR)) / 'cache_invalidated_at'


class FacadeCache:
    def __init__(self):
        self._data = {}
        self._last_validated_at = 0.0
        logger.debug("[pid=%d] FacadeCache created (id=%s)", os.getpid(), id(self))

    def _check_invalidation(self):
        """Check if cache should be cleared based on shared invalidation file."""
        try:
            file_mtime = INVALIDATION_FILE.stat().st_mtime
            if file_mtime > self._last_validated_at:
                logger.debug("[pid=%d] Cache invalidated by file (file_mtime=%.3f > last_validated=%.3f)",
                             os.getpid(), file_mtime, self._last_validated_at)
                self._data.clear()
                self._last_validated_at = time.time()
        except FileNotFoundError:
            pass

    @staticmethod
    def signal_invalidation():
        """Signal all workers to clear their caches by touching the invalidation file."""
        INVALIDATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        INVALIDATION_FILE.touch()
        logger.debug("[pid=%d] Cache invalidation signaled", os.getpid())

    def __contains__(self, key):
        self._check_invalidation()
        return key in self._data

    def __getitem__(self, key):
        self._check_invalidation()
        return self._data[key]

    def __setitem__(self, key, value):
        self._check_invalidation()
        self._data[key] = value

    def get(self, key, default=None):
        self._check_invalidation()
        return self._data.get(key, default)

    def keys(self):
        self._check_invalidation()
        return self._data.keys()

    def clear(self):
        """Clear this worker's cache and signal other workers to clear theirs."""
        self._data.clear()
        self._last_validated_at = time.time()
        self.signal_invalidation()

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all entries with keys starting with the given prefix.

        Also signals other workers to clear their caches entirely.
        Returns the number of entries removed from this worker's cache.
        """
        self._check_invalidation()
        keys_to_remove = [k for k in self._data if k.startswith(prefix)]
        for k in keys_to_remove:
            del self._data[k]
        self.signal_invalidation()
        return len(keys_to_remove)

    def __len__(self):
        self._check_invalidation()
        return len(self._data)