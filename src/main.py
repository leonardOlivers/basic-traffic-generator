thonimport argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

# Ensure src directory is on sys.path when running as a script
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from utils.logger import get_logger  # type: ignore
from storage.queue_handler import URLQueue, load_urls_from_file  # type: ignore
from storage.dataset_writer import DatasetWriter  # type: ignore
from traffic.browser_driver import BrowserDriver  # type: ignore
from traffic.session_manager import SessionManager  # type: ignore

def load_schema(schema_path: str) -> Dict[str, Any]:
    if not os.path.exists(schema_path):
        raise FileNotFoundError(f"Input schema not found at {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)

def validate_config(config: Dict[str, Any], schema_path: str, logger: logging.Logger) -> None:
    try:
        from jsonschema import validate
        from jsonschema.exceptions import ValidationError
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("jsonschema not available (%s). Skipping config validation.", exc)
        return

    schema = load_schema(schema_path)
    try:
        validate(instance=config, schema=schema)
    except ValidationError as exc:
        logger.error("Configuration validation failed: %s", exc)
        raise SystemExit(1) from exc

async def run_simulation(config: Dict[str, Any]) -> None:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger = get_logger("traffic-generator")

    urls_file = config["urls_file"]
    if not os.path.isabs(urls_file):
        urls_file = os.path.join(base_dir, urls_file)

    output_file = config["output_file"]
    if not os.path.isabs(output_file):
        output_file = os.path.join(base_dir, output_file)

    urls = load_urls_from_file(urls_file)
    if not urls:
        logger.error("No URLs loaded from %s", urls_file)
        raise SystemExit(1)

    sessions = max(1, int(config.get("sessions", 1)))
    if sessions > 1:
        urls = urls * sessions
        logger.info("Running %d sessions across %d base URLs (%d total visits).",
                    sessions, len(urls) // sessions, len(urls))
    else:
        logger.info("Running a single session across %d URLs.", len(urls))

    queue = URLQueue(urls)
    writer = DatasetWriter(output_file)

    async with BrowserDriver(headless=bool(config.get("headless", True)), logger=logger) as driver:
        manager = SessionManager(
            browser_driver=driver,
            url_queue=queue,
            writer=writer,
            max_interactions=int(config.get("max_interactions", 10)),
            concurrency=int(config.get("concurrency", 3)),
            delay_between_sessions=float(config.get("delay_between_sessions", 0.0)),
            logger=logger,
        )
        await manager.run()

    writer.flush()
    logger.info("Simulation complete. Results written to %s", output_file)

def parse_args() -> Dict[str, Any]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    default_urls = os.path.join("data", "urls.txt")
    default_output = os.path.join("data", "example_output.json")
    schema_path = os.path.join(CURRENT_DIR, "config", "input_schema.json")

    parser = argparse.ArgumentParser(
        description="Basic Traffic Generator using Playwright."
    )
    parser.add_argument(
        "--urls-file",
        default=default_urls,
        help=f"Path to file containing URLs (default: {default_urls})",
    )
    parser.add_argument(
        "--output-file",
        default=default_output,
        help=f"Path to JSON file where results will be stored (default: {default_output})",
    )
    parser.add_argument(
        "--sessions",
        type=int,
        default=1,
        help="Number of sessions (each session iterates over the URLs list).",
    )
    parser.add_argument(
        "--max-interactions",
        type=int,
        default=10,
        help="Maximum automated interactions per URL.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Number of concurrent workers.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browsers in headless mode (default: True).",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Disable headless mode.",
    )
    parser.add_argument(
        "--delay-between-sessions",
        type=float,
        default=0.0,
        help="Optional delay in seconds between processing URLs per worker.",
    )

    args = parser.parse_args()

    headless = True
    if args.no_headless:
        headless = False

    config: Dict[str, Any] = {
        "urls_file": args.urls_file,
        "output_file": args.output_file,
        "sessions": args.sessions,
        "max_interactions": args.max_interactions,
        "concurrency": args.concurrency,
        "headless": headless,
        "delay_between_sessions": args.delay_between_sessions,
    }

    logger = get_logger("config-validator")
    validate_config(config, schema_path=schema_path, logger=logger)
    return config

def main() -> None:
    config = parse_args()
    asyncio.run(run_simulation(config))

if __name__ == "__main__":
    main()