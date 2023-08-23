
from fastapi import APIRouter, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


trace.set_tracer_provider(
    TracerProvider(resource=Resource.create({"service.name": "autogpt"}))
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

monitoring_router = APIRouter()


@monitoring_router.get("/metrics", tags=["monitoring"])
async def get_metrics():
    """
    Endpoint to get Prometheus metrics.
    """
    return Response(prometheus_client.generate_latest(), media_type=CONTENT_TYPE_LATEST)
