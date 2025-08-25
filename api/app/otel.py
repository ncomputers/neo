import os
from fastapi import FastAPI
from starlette.requests import Request
from opentelemetry import trace
from .db import engine


def init_tracing(app: FastAPI) -> None:
    """Configure OpenTelemetry tracing if an exporter endpoint is set."""
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased, ParentBased
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    service_name = os.getenv("OTEL_SERVICE_NAME", "neo-api")
    ratio = float(os.getenv("OTEL_SAMPLER_RATIO", "0.1"))
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(
        resource=resource, sampler=ParentBased(TraceIdRatioBased(ratio))
    )
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    )
    trace.set_tracer_provider(provider)

    def _request_hook(span, scope):
        if span is None:
            return
        request = Request(scope)
        span.set_attribute("path", request.url.path)
        tenant = request.path_params.get("tenant") or request.path_params.get("tenant_id")
        if tenant:
            span.set_attribute("tenant", tenant)
        request_id = getattr(request.state, "correlation_id", None) or request.headers.get(
            "X-Request-ID"
        )
        if request_id:
            span.set_attribute("request_id", request_id)

    FastAPIInstrumentor().instrument_app(
        app, tracer_provider=provider, request_hook=_request_hook
    )
    SQLAlchemyInstrumentor().instrument(engine=engine, tracer_provider=provider)
    RedisInstrumentor().instrument(tracer_provider=provider)
