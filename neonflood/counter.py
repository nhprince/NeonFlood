"""
neonflood/counter.py
====================
Thread-safe shared integer counters for use across multiprocessing workers.

Uses multiprocessing.Value with Lock for atomic increments so that hit/fail
counts are accurate even when dozens of processes update them simultaneously.

Also tracks a per-second RPS tick counter that is periodically drained by the
stats thread to compute requests-per-second without requiring extra storage.
"""

from multiprocessing import Value


class SafeCounter:
    """
    Atomic hit/fail/rps counters backed by multiprocessing.Value.

    All increment operations are protected by a Lock to prevent lost
    updates due to race conditions between worker processes.

    Attributes
    ----------
    hits      : shared int — total successful responses (HTTP < 400)
    fails     : shared int — total failed/blocked responses
    rps_tick  : shared int — requests since last reset (used for RPS calc)
    """

    def __init__(self, manager):
        """
        Parameters
        ----------
        manager : multiprocessing.Manager instance
            Must be a live Manager so shared Values can cross process boundaries.
        """
        self.hits     = manager.Value('i', 0)
        self.fails    = manager.Value('i', 0)
        self.rps_tick = manager.Value('i', 0)
        self._hl      = manager.Lock()
        self._fl      = manager.Lock()
        self._rl      = manager.Lock()

    def add_hit(self):
        """Atomically increment the hit counter and the RPS tick."""
        with self._hl:
            self.hits.value += 1
        with self._rl:
            self.rps_tick.value += 1

    def add_fail(self):
        """Atomically increment the fail counter."""
        with self._fl:
            self.fails.value += 1

    def reset_rps_tick(self):
        """
        Atomically read and reset the RPS tick counter.

        Returns
        -------
        int
            The number of hits recorded since the last call to this method.
            Call this once per second to get the current requests-per-second.
        """
        with self._rl:
            val = self.rps_tick.value
            self.rps_tick.value = 0
        return val

    @property
    def hit_count(self):
        """Total successful hits so far."""
        return self.hits.value

    @property
    def fail_count(self):
        """Total failed requests so far."""
        return self.fails.value
