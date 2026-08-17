#!/usr/bin/env python3
"""Template client: discover the app, call it through the orchestrator, pay inline.

Livepeer integration (grep `# Livepeer:`):
  1. runner_selector()  — discover orchestrators advertising the app
  2. call_runner()      — call it through the orchestrator; on the paid path this
                          answers the 402 payment challenge inline. Single-shot needs
                          no reserve/stop: the orchestrator reserves a session for the
                          one request and releases it when the response returns.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from livepeer_gateway.errors import LivepeerGatewayError
from livepeer_gateway.live_runner import call_runner
from livepeer_gateway.selection import runner_selector

DEFAULT_DISCOVERY = "https://localhost:8935/discovery"
APP_ID = "your-org/your-app"  # keep in step with runner.py

log = logging.getLogger("your-app-client")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call the app on the network.")
    parser.add_argument("--discovery", default=DEFAULT_DISCOVERY)
    parser.add_argument("--input", default="hello")
    parser.add_argument(
        "--signer", default="", help="Remote signer base URL (on-chain/paid path)."
    )
    return parser.parse_args()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = _parse_args()
    try:
        cursor = await runner_selector(  # Livepeer: 1
            discovery_url=args.discovery,  # omit if the signer does discovery itself
            app=APP_ID,
        )
        runner = cursor.candidates[0]
        log.info("app_url=%s", runner.url)

        result = await call_runner(  # Livepeer: 2
            runner=runner,  # discovery metadata tells call_runner the price unit
            runner_url=runner.url.rstrip("/") + "/run",
            payload={"input": args.input},
            signer_url=args.signer.strip() or None,
        )
        print(result.data)
    except LivepeerGatewayError as exc:
        raise SystemExit(f"ERROR: {exc}") from exc


if __name__ == "__main__":
    asyncio.run(main())
