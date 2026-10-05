from contextlib import nullcontext
from app.config import get_settings

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
except Exception:  # pragma: no cover - optional dependency safety
    trace = None


def setup_telemetry(app=None, engine=None) -> None:
    if trace is None:
        return
    settings = get_settings()
    provider = TracerProvider(resource=Resource.create({'service.name': 'agentic-campaign-manager'}))
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint) if settings.otel_exporter_otlp_endpoint else ConsoleSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
    if engine is not None:
        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    RedisInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()


def agent_span(node_name: str):
    if trace is None:
        return nullcontext()
    return trace.get_tracer('agentic-campaign-manager').start_as_current_span(f'agent.{node_name}')
