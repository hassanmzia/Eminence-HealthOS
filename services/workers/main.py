"""
HealthOS Worker — Kafka consumer for processing agent events.

Consumes events from Kafka topics (device data, vitals, lab results)
and routes them through the orchestrator pipeline.
"""

import asyncio
import json
import logging
import signal
from typing import Optional

logger = logging.getLogger("healthos.worker")

# Kafka topics this worker subscribes to
TOPICS = [
    "healthos.vitals.ingest",
    "healthos.labs.ingest",
    "healthos.devices.ingest",
    "healthos.alerts.trigger",
    "healthos.agents.request",
]


class HealthOSWorker:
    """Async Kafka consumer that feeds events into the orchestrator."""

    def __init__(self):
        self._consumer = None
        self._running = False
        self._orchestrator = None

    async def start(self) -> None:
        """Initialize consumer and orchestrator, then start consuming."""
        from platform.config.settings import get_settings
        from platform.orchestrator.engine import OrchestratorEngine

        settings = get_settings()
        self._orchestrator = OrchestratorEngine()

        # Initialize Kafka consumer
        try:
            from aiokafka import AIOKafkaConsumer

            self._consumer = AIOKafkaConsumer(
                *TOPICS,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=settings.kafka_group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
            )
            await self._consumer.start()
            logger.info("Kafka consumer started on topics: %s", TOPICS)
        except Exception as e:
            logger.error("Failed to connect to Kafka: %s", e)
            logger.info("Running in standalone mode without Kafka")
            self._consumer = None

        # Initialize orchestrator agents
        await self._orchestrator.initialize_all()

        self._running = True
        await self._consume_loop()

    async def _consume_loop(self) -> None:
        """Main consumption loop."""
        if not self._consumer:
            logger.info("No Kafka consumer — worker idle")
            while self._running:
                await asyncio.sleep(5)
            return

        try:
            async for message in self._consumer:
                if not self._running:
                    break

                try:
                    await self._handle_message(
                        topic=message.topic,
                        payload=message.value,
                    )
                except Exception as e:
                    logger.error(
                        "Error processing message from %s: %s",
                        message.topic,
                        e,
                    )
        finally:
            await self._consumer.stop()

    async def _handle_message(self, topic: str, payload: dict) -> None:
        """Route a Kafka message to the appropriate orchestrator pipeline."""
        from platform.orchestrator.engine import OrchestratorContext

        logger.info("Received message on topic=%s", topic)

        trigger_map = {
            "healthos.vitals.ingest": "device",
            "healthos.labs.ingest": "event",
            "healthos.devices.ingest": "device",
            "healthos.alerts.trigger": "event",
            "healthos.agents.request": "manual",
        }

        context = OrchestratorContext(
            patient_id=payload.get("patient_id"),
            tenant_id=payload.get("tenant_id", "default"),
            trigger=trigger_map.get(topic, "event"),
            trigger_data=payload,
        )

        await self._orchestrator.run_pipeline(context)

        if context.errors:
            logger.warning(
                "Pipeline completed with %d errors for trace=%s",
                len(context.errors),
                context.trace_id[:12],
            )

    async def stop(self) -> None:
        """Graceful shutdown."""
        logger.info("Worker shutting down...")
        self._running = False
        if self._orchestrator:
            await self._orchestrator.shutdown_all()


async def main():
    """Entry point for the worker process."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    )

    worker = HealthOSWorker()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
