
from fastapi import APIRouter, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_fastapi_instrumentor import Instrumentator


trace.set_tracer_provider(
    TracerProvider(resource=Resource.create({"service.name": "autogpt"}))
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

monitoring_router = APIRouter()
Instrumentator().instrument_app(monitoring_router)
FastAPIInstrumentor.instrument_app(monitoring_router)


@monitoring_router.get("/metrics", tags=["monitoring"])
async def get_metrics():
    """
    Endpoint to get Prometheus metrics.
    """
    return Response(prometheus_client.generate_latest(), media_type=CONTENT_TYPE_LATEST)
