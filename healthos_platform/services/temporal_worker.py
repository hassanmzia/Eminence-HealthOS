"""
Eminence HealthOS — Temporal Worker Entrypoint

Standalone process that connects to the Temporal server, registers all
HealthOS workflows and activities, and polls the "healthos-operations"
task queue.  Designed to run as a Docker Compose service:

    python -m healthos_platform.services.temporal_worker

Gracefully shuts down on SIGINT / SIGTERM.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("healthos.temporal.worker")

TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TASK_QUEUE = "healthos-operations"


async def run_worker() -> None:
    """Connect to Temporal, build the worker, and run until cancelled."""

    # Delay imports so the module can be loaded without the SDK installed
    # (mirrors the guard in temporal.py).
    try:
        from temporalio.client import Client
        from temporalio.worker import Worker
    except ImportError:
        logger.critical(
            "temporalio SDK is not installed — "
            "add 'temporalio' to your requirements and rebuild the image"
        )
        sys.exit(1)

    from healthos_platform.services.temporal import (
        CriticalAlertWorkflow,
        PatientOnboardingWorkflow,
        RPMReviewWorkflow,
        create_encounter_activity,
        run_agent_activity,
        send_notification_activity,
        update_patient_status_activity,
    )

    logger.info(
        "Connecting to Temporal server at %s …",
        TEMPORAL_ADDRESS,
    )
    client = await Client.connect(TEMPORAL_ADDRESS)
    logger.info("Connected to Temporal server")

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            PatientOnboardingWorkflow,
            CriticalAlertWorkflow,
            RPMReviewWorkflow,
        ],
        activities=[
            run_agent_activity,
            send_notification_activity,
            create_encounter_activity,
            update_patient_status_activity,
        ],
    )

    logger.info(
        "Starting Temporal worker on task queue '%s' with %d workflows and %d activities",
        TASK_QUEUE,
        3,
        4,
    )

    # Set up graceful shutdown on SIGINT / SIGTERM
    shutdown_event = asyncio.Event()

    def _handle_signal(sig: signal.Signals) -> None:
        logger.info("Received %s — initiating graceful shutdown …", sig.name)
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal, sig)

    # Run the worker until a shutdown signal is received
    async with worker:
        await shutdown_event.wait()

    logger.info("Temporal worker shut down cleanly")


def main() -> None:
    """Entrypoint for ``python -m healthos_platform.services.temporal_worker``."""
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker interrupted — exiting")


if __name__ == "__main__":
    main()
