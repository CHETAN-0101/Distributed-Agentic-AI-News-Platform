"""
AgentOS — OpenTelemetry tracing bootstrap.
Import and call configure_tracing() once at service startup.
"""
from __future__ import annotations

from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat


def configure_tracing(
    service_name: str,
    service_version: str = "0.1.0",
    otlp_endpoint: Optional[str] = None,
    console_export: bool = False,
) -> TracerProvider:
    """
    Bootstrap OpenTelemetry tracing. Call once at application startup.

    Args:
        service_name:    Name of this service (used in Jaeger spans).
        service_version: Version string for resource attributes.
        otlp_endpoint:   OTLP gRPC endpoint (e.g. http://jaeger:4317).
                         If None, reads from settings.
        console_export:  Also print spans to stdout (useful for development).

    Returns:
        The configured TracerProvider.
    """
    if otlp_endpoint is None:
        try:
            from shared.config import settings
            otlp_endpoint = settings.otel_exporter_otlp_endpoint
            enabled = settings.otel_enabled
        except Exception:
            enabled = False
    else:
        enabled = True

    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": "development",
        }
    )

    provider = TracerProvider(resource=resource)

    if enabled and otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if console_export:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)

    # Use B3 propagation for cross-service context propagation
    set_global_textmap(B3MultiFormat())

    return provider


def instrument_fastapi(app: object) -> None:
    """Instrument a FastAPI app instance."""
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]


def instrument_httpx() -> None:
    """Instrument all httpx clients."""
    HTTPXClientInstrumentor().instrument()


def instrument_sqlalchemy(engine: object) -> None:
    """Instrument SQLAlchemy engine."""
    SQLAlchemyInstrumentor().instrument(engine=engine, enable_commenter=True)


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a named tracer."""
    return trace.get_tracer(name)
