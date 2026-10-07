import json
import logging
import time
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from app.api.routes.files import router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import request_id as request_context

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("geomeasure")
app = FastAPI(title="GeoMeasure API", version="1.0.0")
settings = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST"], allow_headers=["Content-Type"], expose_headers=["X-Request-ID"])


def error(code, message, status):
    return JSONResponse({"error": {"code": code, "message": message, "details": None}}, status_code=status)


class BodyLimitMiddleware:
    def __init__(self, app, limit):
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        length = dict(scope["headers"]).get(b"content-length")
        if length and (not length.isdigit() or int(length) > self.limit):
            return await error("FILE_TOO_LARGE", "Request exceeds the upload limit.", 413)(scope, receive, send)
        size = 0
        exceeded = False

        async def bounded_receive():
            nonlocal size, exceeded
            message = await receive()
            size += len(message.get("body", b""))
            if size > self.limit:
                exceeded = True
                raise AppError("FILE_TOO_LARGE", "Request exceeds the upload limit.", 413)
            return message

        async def bounded_send(message):
            # Multipart parsers can translate a receive exception into HTTP 400.
            # Preserve the size error contract even for chunked requests.
            if exceeded:
                if message["type"] == "http.response.start":
                    await error("FILE_TOO_LARGE", "Request exceeds the upload limit.", 413)(scope, receive, send)
                return
            await send(message)
        await self.app(scope, bounded_receive, bounded_send)


app.add_middleware(BodyLimitMiddleware, limit=(settings.max_upload_size_mb + 1) * 1024 * 1024)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = str(uuid4())
    request_context.set(request_id)
    started = time.monotonic()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(json.dumps({"request_id": request_id, "stage": "http", "status": response.status_code, "duration": round(time.monotonic() - started, 3)}))
    return response


@app.exception_handler(AppError)
async def app_error(request, exc):
    return error(exc.code, exc.message, exc.status)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    return error("INVALID_REQUEST", "Check the request fields, identifier and pagination values.", 422)


@app.exception_handler(HTTPException)
async def http_error(request, exc):
    return error("HTTP_ERROR", "The request could not be accepted.", exc.status_code)


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logger.error(json.dumps({"stage": "http", "error_code": "INTERNAL_ERROR", "exception_type": type(exc).__name__}))
    return error("INTERNAL_ERROR", "The service could not complete this request.", 500)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(router)
