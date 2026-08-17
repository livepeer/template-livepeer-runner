#!/usr/bin/env python3
"""Template app: a normal aiohttp service, made callable on the Livepeer network.

Replace `/run` with your own endpoints. Being on the network doesn't change how you
write them: the orchestrator is a transparent reverse proxy, so whatever you expose
is what callers reach.

Livepeer integration (grep `# Livepeer:`):
  1. register_runner()     — announce the app to the orchestrator (startup)
  2. registration.close()  — deregister (cleanup)
"""

from __future__ import annotations

import argparse
import logging
from contextlib import suppress

from aiohttp import web

from livepeer_gateway.live_runner import register_runner

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8989
# What callers discover and match on, exactly. Rename it to your app.
APP_ID = "your-org/your-app"

log = logging.getLogger("your-app")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Live Runner app.")
    parser.add_argument("--orchestrator", default="https://localhost:8935")
    parser.add_argument("--orchSecret", default="abcdef")
    parser.add_argument("--runner-url", default=f"http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help="Bind address (use 0.0.0.0 in containers)."
    )
    parser.add_argument(
        "--price",
        type=float,
        default=0,
        help="Price in USD per call (0 = free, the offchain default).",
    )
    parser.add_argument(
        "--capacity",
        type=int,
        default=1,
        help="Concurrent sessions the orchestrator may route here.",
    )
    return parser.parse_args()


async def _handle_run(request: web.Request) -> web.Response:
    # An ordinary handler. Reject a malformed body rather than guessing at it.
    try:
        payload = await request.json()
    except Exception:
        payload = None
    if not isinstance(payload, dict):
        raise web.HTTPBadRequest(text="body must be a JSON object")

    value = payload.get("input", "")
    return web.json_response({"output": f"you sent: {value}"})


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = _parse_args()

    async def _on_startup(app: web.Application) -> None:
        app["registration"] = await register_runner(  # Livepeer: 1
            args.orchestrator,
            secret=args.orchSecret,
            runner_url=args.runner_url,
            app=APP_ID,
            mode="single-shot",  # one request in, one response out
            price=args.price,
            unit="fixed",  # one flat payment per call, not per-second metering
            capacity=args.capacity,
        )
        log.info(
            "registered runner_id=%s orchestrator=%s",
            app["registration"].runner_id,
            app["registration"].orchestrator_url,
        )

    async def _on_cleanup(app: web.Application) -> None:
        # Deregister on shutdown so the orchestrator stops advertising us at once,
        # instead of waiting for the heartbeat TTL to expire.
        with suppress(Exception):
            await app["registration"].close()  # Livepeer: 2

    app = web.Application()
    app.router.add_post("/run", _handle_run)
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
    web.run_app(app, host=args.host, port=DEFAULT_PORT)


if __name__ == "__main__":
    main()
