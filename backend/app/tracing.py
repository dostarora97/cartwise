"""OpenTelemetry tracing via Pydantic Logfire — no Logfire cloud."""

import logfire

from app.config import settings


def setup_tracing(app) -> None:
    """Configure tracing based on environment.

    - Development: ConsoleSpanExporter (pretty-printed to stdout)
    - Production: CloudTraceSpanExporter (Google Cloud Trace via ADC)
    - Testing: disabled entirely
    """
    if not settings.get("TRACING_ENABLED", True):
        logfire.configure(send_to_logfire=False)
        return

    exporter = settings.get("TRACING_EXPORTER", "console")
    additional_processors = []

    if exporter == "gcp":
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        additional_processors.append(BatchSpanProcessor(CloudTraceSpanExporter()))

    elif exporter == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

        additional_processors.append(SimpleSpanProcessor(ConsoleSpanExporter()))

    logfire.configure(
        send_to_logfire=False,
        service_name=settings.TRACING_SERVICE_NAME,
        additional_span_processors=additional_processors,
    )

    from app.database import engine

    logfire.instrument_fastapi(app, excluded_urls="/health")
    logfire.instrument_sqlalchemy(engine=engine)
    logfire.instrument_httpx()
    logfire.instrument_asyncpg()
