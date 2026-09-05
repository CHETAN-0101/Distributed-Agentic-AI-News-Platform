"""
AgentOS — BaseAgent

All agents inherit from this class. It provides:
- Self-registration with the Agent Registry
- Periodic heartbeat
- Task consumption from RabbitMQ
- Schema validation (input AND output)
- Circuit breaker awareness
- Retry logic
- Health endpoint
- Prometheus metrics
- OpenTelemetry spans per task
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Optional
from uuid import uuid4

from prometheus_client import Counter, Histogram, Gauge, start_http_server

from shared.config import settings
from shared.logging import get_logger, configure_logging
from shared.messaging.consumer import EventConsumer
from shared.messaging.idempotency import IdempotencyStore
from shared.messaging.publisher import EventPublisher
from shared.messaging.retry import ExponentialBackoff
from shared.schemas.agent import AgentRegistration, AgentHealthReport
from shared.schemas.events import BaseEvent, TaskCompletedEvent, TaskFailedEvent
from shared.schemas.task import TaskInput, TaskOutput, TaskStatus
from shared.tracing import configure_tracing, get_tracer
from shared.utilities.llm.factory import get_llm_provider
from .registry_client import RegistryClient

logger = get_logger(__name__)


class BaseAgent(ABC):
    """
    Base class for all AgentOS agents.

    Subclasses must implement:
        - agent_id: str property
        - name: str property
        - version: str property
        - capabilities: list[str] property
        - required_permissions: list[str] property
        - execute(task_input: TaskInput) -> TaskOutput: the core logic

    Usage:
        class MyAgent(BaseAgent):
            @property
            def agent_id(self): return "my-agent"
            ...
            async def execute(self, task: TaskInput) -> TaskOutput: ...

        agent = MyAgent()
        await agent.run()
    """

    # -------------------------------------------------------------------------
    # Identity (must be implemented by subclasses)
    # -------------------------------------------------------------------------
    @property
    @abstractmethod
    def agent_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    @abstractmethod
    def capabilities(self) -> list[str]: ...

    @property
    @abstractmethod
    def required_permissions(self) -> list[str]: ...

    @property
    def description(self) -> str:
        return ""

    @property
    def cost_estimate(self) -> Optional[float]:
        return None

    # -------------------------------------------------------------------------
    # Core Logic (must be implemented by subclasses)
    # -------------------------------------------------------------------------
    @abstractmethod
    async def execute(self, task_input: TaskInput) -> TaskOutput:
        """
        Process a task and return a result.

        Args:
            task_input: Validated TaskInput envelope.

        Returns:
            TaskOutput with status, result, evidence, confidence.
        """
        ...

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------
    def __init__(self) -> None:
        configure_logging(
            service_name=settings.service_name or self.agent_id,
            log_level=settings.log_level,
            json_output=settings.is_production,
        )
        configure_tracing(
            service_name=settings.service_name or self.agent_id,
            otlp_endpoint=settings.otel_exporter_otlp_endpoint,
        )

        self._tracer = get_tracer(self.agent_id)
        self._llm = get_llm_provider()

        # Infrastructure clients
        self._publisher = EventPublisher()
        self._idempotency = IdempotencyStore()
        self._registry = RegistryClient()
        self._consumer: Optional[EventConsumer] = None

        # State
        self._running = False
        self._task_queue = f"tasks.{self.agent_id}"

        # Prometheus metrics
        self._tasks_total = Counter(
            "agentos_tasks_total",
            "Total tasks processed",
            ["agent_id", "status"],
        )
        self._task_duration = Histogram(
            "agentos_task_duration_seconds",
            "Task execution duration",
            ["agent_id", "capability"],
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120],
        )
        self._task_errors = Counter(
            "agentos_task_errors_total",
            "Total task errors",
            ["agent_id", "error_type"],
        )
        self._confidence_gauge = Gauge(
            "agentos_task_confidence",
            "Last task confidence score",
            ["agent_id"],
        )

    async def startup(self) -> None:
        """Connect to all infrastructure and register with the registry."""
        logger.info("Agent starting up", agent_id=self.agent_id, version=self.version)

        await self._publisher.connect()
        await self._idempotency.connect()
        await self._registry.connect()

        # Register with Agent Registry
        registration = AgentRegistration(
            agent_id=self.agent_id,
            name=self.name,
            description=self.description,
            version=self.version,
            host=settings.service_host,
            port=settings.agent_port,
            capabilities=self.capabilities,
            required_permissions=self.required_permissions,
            cost_estimate=self.cost_estimate,
        )
        await self._registry.register(registration)

        # Set up consumer for the agent's task queue
        self._consumer = EventConsumer(
            queue_name=self._task_queue,
            idempotency_store=self._idempotency,
            retry_policy=ExponentialBackoff(),
        )
        self._consumer.register_handler("task.created", self._handle_task_event)
        await self._consumer.start()

        # Start Prometheus metrics server
        start_http_server(settings.agent_port + 100)  # e.g. agent on 9001, metrics on 9101

        logger.info("Agent ready", agent_id=self.agent_id)

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("Agent shutting down", agent_id=self.agent_id)
        self._running = False
        if self._consumer:
            await self._consumer.stop()
        await self._publisher.close()
        await self._idempotency.close()
        await self._registry.close()

    async def run(self) -> None:
        """Main entry point — runs until cancelled."""
        await self.startup()
        self._running = True

        # Start heartbeat loop
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            while self._running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            heartbeat_task.cancel()
            await self.shutdown()

    # -------------------------------------------------------------------------
    # Task Handling
    # -------------------------------------------------------------------------
    async def _handle_task_event(
        self,
        event: BaseEvent,
        message: Any,
    ) -> None:
        """Deserialize and dispatch a task.created event."""
        try:
            task_input = TaskInput.model_validate(event.payload)
        except Exception as e:
            logger.error("Task input validation failed", error=str(e), payload=event.payload)
            self._task_errors.labels(agent_id=self.agent_id, error_type="validation").inc()
            return

        await self._process_task(task_input)

    async def _process_task(self, task_input: TaskInput) -> None:
        """Execute a task, publish result, handle errors."""
        start_time = time.monotonic()
        task_id = task_input.task_id
        capability = task_input.capability

        logger.info(
            "Processing task",
            task_id=task_id,
            capability=capability,
            agent_id=self.agent_id,
        )

        with self._tracer.start_as_current_span(
            f"agent.{self.agent_id}.{capability}",
            attributes={
                "agent.id": self.agent_id,
                "task.id": task_id,
                "task.capability": capability,
                "task.priority": task_input.priority.value,
            },
        ):
            try:
                output = await self.execute(task_input)
                duration_ms = int((time.monotonic() - start_time) * 1000)
                output.execution_time_ms = duration_ms

                # Publish success event
                await self._publisher.publish(
                    TaskCompletedEvent(
                        tenant_id=task_input.tenant_id,
                        workflow_id=task_input.workflow_id,
                        task_id=task_id,
                        producer=self.agent_id,
                        correlation_id=task_input.correlation_id,
                        trace_id=task_input.trace_id,
                        payload=output.model_dump(),
                    )
                )

                self._tasks_total.labels(agent_id=self.agent_id, status="completed").inc()
                self._task_duration.labels(
                    agent_id=self.agent_id, capability=capability
                ).observe((time.monotonic() - start_time))

                if output.confidence is not None:
                    self._confidence_gauge.labels(agent_id=self.agent_id).set(output.confidence)

                logger.info(
                    "Task completed",
                    task_id=task_id,
                    duration_ms=duration_ms,
                    confidence=output.confidence,
                )

            except Exception as exc:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                error_output = TaskOutput(
                    task_id=task_id,
                    agent_id=self.agent_id,
                    status=TaskStatus.FAILED,
                    errors=[str(exc)],
                    execution_time_ms=duration_ms,
                    trace_id=task_input.trace_id,
                    correlation_id=task_input.correlation_id,
                )
                await self._publisher.publish(
                    TaskFailedEvent(
                        tenant_id=task_input.tenant_id,
                        workflow_id=task_input.workflow_id,
                        task_id=task_id,
                        producer=self.agent_id,
                        correlation_id=task_input.correlation_id,
                        payload=error_output.model_dump(),
                    )
                )
                self._tasks_total.labels(agent_id=self.agent_id, status="failed").inc()
                self._task_errors.labels(agent_id=self.agent_id, error_type=type(exc).__name__).inc()

                logger.error(
                    "Task failed",
                    task_id=task_id,
                    error=str(exc),
                    exc_info=True,
                )

    # -------------------------------------------------------------------------
    # Heartbeat
    # -------------------------------------------------------------------------
    async def _heartbeat_loop(self) -> None:
        """Send heartbeat to Agent Registry every N seconds."""
        while self._running:
            try:
                report = AgentHealthReport(
                    agent_id=self.agent_id,
                    status="healthy",
                )
                await self._registry.heartbeat(report)
            except Exception as e:
                logger.warning("Heartbeat failed", error=str(e))

            await asyncio.sleep(settings.agent_heartbeat_interval)
