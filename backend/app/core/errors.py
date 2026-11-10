from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: list | None = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {"code": exc.code, "message": exc.message, "details": exc.details},
            "meta": {"request_id": str(getattr(request.state, "request_id", ""))},
        },
    )


async def validation_error_handler(request: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(x) for x in e["loc"]), "message": e["msg"]} for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Submitted data is invalid",
                "details": details,
            },
            "meta": {"request_id": str(getattr(request.state, "request_id", ""))},
        },
    )
