"""GodCV CLI entry point.

Usage:
    godcv run              Start the server (port 9000)
    godcv run --port 8080  Start on custom port
    godcv run --dev        Start with auto-reload + CORS for Vite dev server
"""
import argparse
import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)-25s %(message)s"
LOG_DATE = "%H:%M:%S"


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format=LOG_FORMAT, datefmt=LOG_DATE, level=level, stream=sys.stdout)
    # Quiet noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)


def cmd_build(args):
    import subprocess
    setup_logging()
    logger = logging.getLogger("godcv")

    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    if not (frontend_dir / "package.json").exists():
        logger.error("frontend/ directory not found at %s", frontend_dir)
        sys.exit(1)

    logger.info("Installing frontend dependencies...")
    subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=True)

    logger.info("Building frontend...")
    subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), check=True)

    logger.info("Frontend built successfully at %s/dist", frontend_dir)


def cmd_run(args):
    import uvicorn
    setup_logging(args.verbose)
    logger = logging.getLogger("godcv")

    logger.info("Starting GodCV on port %d", args.port)
    if args.dev:
        logger.info("Dev mode: auto-reload ON, CORS for localhost:3000")

    uvicorn.run(
        "backend.main:app",
        host=args.host,
        port=args.port,
        reload=args.dev,
        log_level="debug" if args.verbose else "info",
    )


def main():
    parser = argparse.ArgumentParser(
        prog="godcv",
        description="GodCV - AI-powered resume tailoring",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("build", help="Build the frontend (npm install + npm run build)")

    run_parser = sub.add_parser("run", help="Start the GodCV server")
    run_parser.add_argument("--port", type=int, default=9000, help="Port (default: 9000)")
    run_parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    run_parser.add_argument("--dev", action="store_true", help="Dev mode with auto-reload")
    run_parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")

    args = parser.parse_args()

    if args.command == "build":
        cmd_build(args)
    elif args.command == "run":
        cmd_run(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
