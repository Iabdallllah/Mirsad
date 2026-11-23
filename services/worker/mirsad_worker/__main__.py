"""Phase 0 worker entrypoint: idle stub.

Keeps the service container alive without consuming the queue or making any
outbound request. Phase 1 replaces this with the SKIP LOCKED queue consumer
and LangGraph orchestrator (plan.md §3.2, §11.2).
"""

from __future__ import annotations

import asyncio
import logging
import signal

from mirsad_worker.config import WorkerSettings

logger = logging.getLogger("mirsad.worker")


async def run() -> None:
    settings = WorkerSettings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    logger.info(
        "worker stub starting (app_env=%s, caps: %s min / %s tokens / %s llm calls)",
        settings.app_env,
        settings.scan_max_duration_min,
        settings.scan_max_tokens,
        settings.scan_max_llm_calls,
    )
    logger.info("Phase 0 stub: scan engine arrives in Phase 1; no queue consumption yet")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()
    logger.info("worker stub shutting down")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
