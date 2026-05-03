"""GodCV CLI entry point.

Usage:
    godcv dev              Start backend + frontend dev servers (hot-reload)
    godcv run              Start production server (serves built frontend)
    godcv run --port 8080  Start on custom port
    godcv build            Build the frontend
"""
import argparse
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)-25s %(message)s"
LOG_DATE = "%H:%M:%S"

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE, level=level, stream=sys.stdout)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


def cmd_build(args):
    setup_logging()
    logger = logging.getLogger("godcv")

    if not (FRONTEND_DIR / "package.json").exists():
        logger.error("frontend/ directory not found at %s", FRONTEND_DIR)
        sys.exit(1)

    logger.info("Installing frontend dependencies...")
    subprocess.run(["npm", "install"], cwd=str(FRONTEND_DIR), check=True)

    logger.info("Building frontend...")
    subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), check=True)

    logger.info("Frontend built successfully at %s/dist", FRONTEND_DIR)


def _is_port_in_use(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _port_listeners(port: int) -> list[tuple[int, str]]:
    """Return [(pid, command_line)] for processes listening on the TCP port."""
    try:
        lsof = subprocess.run(
            ["lsof", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
            capture_output=True, text=True, check=False,
        )
    except FileNotFoundError:
        return []
    pids = [int(p) for p in lsof.stdout.split() if p.strip().isdigit()]
    out = []
    for pid in pids:
        try:
            ps = subprocess.run(
                ["ps", "-p", str(pid), "-o", "command="],
                capture_output=True, text=True, check=False,
            )
            out.append((pid, ps.stdout.strip()))
        except FileNotFoundError:
            out.append((pid, ""))
    return out


def _looks_like_godcv(cmd: str) -> bool:
    """Heuristic: is this a uvicorn/godcv process we're safe to auto-kill?"""
    cmd_l = cmd.lower()
    return ("uvicorn" in cmd_l and "backend.main:app" in cmd_l) or "godcv" in cmd_l


def _ensure_port_free(port: int, label: str, logger: logging.Logger) -> bool:
    """Free the port if a stale godcv owns it. Return True if free (or freed).

    If a non-godcv process owns the port, log who and return False — the caller
    should exit and let the user resolve the conflict.
    """
    listeners = _port_listeners(port)
    if not listeners:
        return not _is_port_in_use(port)  # may still be bound by something lsof missed

    godcv_pids = [pid for pid, cmd in listeners if _looks_like_godcv(cmd)]
    foreign = [(pid, cmd) for pid, cmd in listeners if not _looks_like_godcv(cmd)]

    if foreign:
        logger.error("Port %d (%s) is held by another application:", port, label)
        for pid, cmd in foreign:
            logger.error("  PID %d  %s", pid, cmd)
        logger.error("Stop that process or rerun with a different port "
                     "(e.g. `godcv dev --port 9002 --frontend-port 3002`).")
        return False

    if godcv_pids:
        logger.warning("Port %d held by stale godcv PID(s) %s — terminating", port, godcv_pids)
        for pid in godcv_pids:
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline and any(_pid_alive(pid) for pid in godcv_pids):
            time.sleep(0.1)
        for pid in godcv_pids:
            if _pid_alive(pid):
                try:
                    os.kill(pid, signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    pass
    return not _is_port_in_use(port)


def cmd_dev(args):
    """Start both backend (uvicorn --reload) and frontend (vite dev) in one command."""
    setup_logging(args.verbose)
    logger = logging.getLogger("godcv")

    if not (FRONTEND_DIR / "package.json").exists():
        logger.error("frontend/ directory not found at %s", FRONTEND_DIR)
        sys.exit(1)

    backend_port = args.port
    frontend_port = args.frontend_port

    # Pre-flight: clear any stale godcv process holding our ports from a previous run.
    # If a *different* application owns the port, bail out with a clear message
    # rather than blindly killing it.
    for port, label in ((backend_port, "backend"), (frontend_port, "frontend")):
        if _is_port_in_use(port) and not _ensure_port_free(port, label, logger):
            sys.exit(1)

    logger.info("Starting GodCV dev mode")
    logger.info("  Backend:  http://localhost:%d (auto-reload)", backend_port)
    logger.info("  Frontend: http://localhost:%d (hot-reload, proxies /api -> :%d)", frontend_port, backend_port)
    logger.info("  Open http://localhost:%d in your browser", frontend_port)
    logger.info("  Press Ctrl+C to stop both")

    dev_env = {
        **os.environ,
        "GODCV_BACKEND_PORT": str(backend_port),
        "GODCV_FRONTEND_PORT": str(frontend_port),
    }
    # WeasyPrint needs libgobject/libpango on macOS via Homebrew. Inject the
    # Homebrew lib path so PDF export works without the user having to set
    # DYLD_FALLBACK_LIBRARY_PATH in their shell profile.
    if sys.platform == "darwin" and "DYLD_FALLBACK_LIBRARY_PATH" not in dev_env:
        for brew_lib in ("/opt/homebrew/lib", "/usr/local/lib"):
            if os.path.isdir(brew_lib):
                dev_env["DYLD_FALLBACK_LIBRARY_PATH"] = brew_lib
                break

    procs = []
    shutting_down = {"v": False}

    def _signal_group(p: subprocess.Popen, sig: int) -> None:
        try:
            os.killpg(os.getpgid(p.pid), sig)
        except (OSError, ProcessLookupError):
            pass

    def _wait_all(timeout: float) -> None:
        deadline = time.monotonic() + timeout
        for p in procs:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                p.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                pass

    def _kill_all():
        if shutting_down["v"]:
            return
        shutting_down["v"] = True

        # Phase 1 — graceful: SIGINT mirrors a Ctrl+C on each subtree.
        # uvicorn's reload supervisor handles SIGINT by tearing down its worker.
        for p in procs:
            if p.poll() is None:
                _signal_group(p, signal.SIGINT)
        _wait_all(timeout=3.0)

        # Phase 2 — escalate to SIGTERM for anything still alive.
        for p in procs:
            if p.poll() is None:
                _signal_group(p, signal.SIGTERM)
        _wait_all(timeout=2.0)

        # Phase 3 — SIGKILL holdouts (covers stuck node/vite, orphaned workers).
        for p in procs:
            if p.poll() is None:
                _signal_group(p, signal.SIGKILL)
                try:
                    p.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass

        # Phase 4 — belt-and-suspenders: if anything still owns the ports
        # (e.g. an orphaned uvicorn worker that escaped its process group),
        # free them before we exit so the next `godcv dev` starts clean.
        for port, label in ((backend_port, "backend"), (frontend_port, "frontend")):
            if _is_port_in_use(port):
                _ensure_port_free(port, label, logger)

    # Translate SIGTERM (e.g. `kill <pid>`) into the same shutdown path as Ctrl+C.
    # Python already converts SIGINT to KeyboardInterrupt by default.
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))

    try:
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app",
             "--host", "0.0.0.0", "--port", str(backend_port), "--reload"],
            env=dev_env,
            start_new_session=True,
        )
        procs.append(backend_proc)

        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
            env=dev_env,
            start_new_session=True,
        )
        procs.append(frontend_proc)

        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    logger.info("Process exited with code %d, stopping all...", ret)
                    raise KeyboardInterrupt
            time.sleep(0.5)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        _kill_all()
        logger.info("Stopped.")


def cmd_run(args):
    import uvicorn
    setup_logging(args.verbose)
    logger = logging.getLogger("godcv")

    if sys.platform == "darwin" and "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ:
        for brew_lib in ("/opt/homebrew/lib", "/usr/local/lib"):
            if os.path.isdir(brew_lib):
                os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = brew_lib
                break

    logger.info("Starting GodCV on http://localhost:%d", args.port)

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="debug" if args.verbose else "info",
    )


def main():
    parser = argparse.ArgumentParser(
        prog="godcv",
        description="GodCV - AI-powered resume tailoring",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("build", help="Build the frontend (npm install + npm run build)")

    dev_parser = sub.add_parser("dev", help="Start backend + frontend with hot-reload (development)")
    dev_parser.add_argument("--port", type=int, default=9001, help="Backend port (default: 9001)")
    dev_parser.add_argument("--frontend-port", type=int, default=3001, help="Frontend port (default: 3001)")
    dev_parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    run_parser = sub.add_parser("run", help="Start production server (serves built frontend)")
    run_parser.add_argument("--port", type=int, default=9001, help="Port (default: 9000)")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    run_parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    elif args.command == "dev":
        cmd_dev(args)
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
