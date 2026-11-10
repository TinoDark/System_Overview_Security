import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.core.config import Settings, settings
from app.core.errors import APIError, api_error_handler, validation_error_handler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def create_app(config: Settings | None = None) -> FastAPI:
    config = config or settings
    config.validate_runtime()
    application = FastAPI(
        title="SOC MVP API",
        version="1.0.0",
        description="Tenant-scoped SOC prototype. Mock connectors and responses are simulation-only.",
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.state.config = config
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Organization-ID",
            "Idempotency-Key",
        ],
        expose_headers=["X-Request-ID"],
    )
    application.include_router(router, prefix=config.api_prefix)
    application.add_exception_handler(APIError, api_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = uuid4()
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request.state.request_id)
        return response

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception):
        logging.getLogger("soc.api").exception("Unhandled API error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An internal error occurred",
                    "details": [],
                },
                "meta": {"request_id": str(getattr(request.state, "request_id", ""))},
            },
        )

    return application


app = create_app()
