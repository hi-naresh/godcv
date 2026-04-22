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
import subprocess
import sys
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


def cmd_dev(args):
    """Start both backend (uvicorn --reload) and frontend (vite dev) in one command."""
    setup_logging(args.verbose)
    logger = logging.getLogger("godcv")

    if not (FRONTEND_DIR / "package.json").exists():
        logger.error("frontend/ directory not found at %s", FRONTEND_DIR)
        sys.exit(1)

    backend_port = args.port
    frontend_port = args.frontend_port
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

    procs = []

    def _kill_all():
        """Kill all child process trees via process group."""
        for p in procs:
            try:
                # Kill the entire process group (parent + all children)
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                except (OSError, ProcessLookupError):
                    p.kill()

    try:
        # Start backend in its own process group so we can kill the whole tree
        backend_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app",
             "--host", "0.0.0.0", "--port", str(backend_port), "--reload"],
            env=dev_env,
            preexec_fn=os.setsid,
        )
        procs.append(backend_proc)

        # Start frontend in its own process group
        frontend_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(FRONTEND_DIR),
            env=dev_env,
            preexec_fn=os.setsid,
        )
        procs.append(frontend_proc)

        # Wait for either to exit
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    logger.info("Process exited with code %d, stopping all...", ret)
                    raise KeyboardInterrupt
            import time
            time.sleep(0.5)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        _kill_all()
        logger.info("Stopped.")


def cmd_run(args):
    import uvicorn
    setup_logging(args.verbose)
    logger = logging.getLogger("godcv")

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
