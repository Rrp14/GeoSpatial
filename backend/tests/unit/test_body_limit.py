import pytest
from fastapi.testclient import TestClient
from app.main import app, BodyLimitMiddleware


def test_content_length_rejected_before_parsing():
    with TestClient(app) as client:
        result = client.post("/api/files/", content=b"small", headers={"Content-Length": str(100 * 1024 * 1024)})
        assert result.status_code == 413
        assert result.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_chunked_receive_is_bounded():
    import asyncio
    from app.core.exceptions import AppError
    async def run():
        async def inner(scope, receive, send):
            await receive()
            await receive()
        async def receive():
            return {"type":"http.request", "body":b"123456", "more_body":True}
        async def send(message):
            pass
        middleware = BodyLimitMiddleware(inner, 10)
        with pytest.raises(AppError) as exc:
            await middleware({"type":"http", "headers":[]}, receive, send)
        assert exc.value.code == "FILE_TOO_LARGE"
    asyncio.run(run())


def test_chunked_multipart_returns_size_contract():
    from fastapi import FastAPI, UploadFile, File
    small_app = FastAPI()
    small_app.add_middleware(BodyLimitMiddleware, limit=100)
    @small_app.post("/")
    def upload(file: UploadFile = File(...)):
        return {"unexpected": True}
    with TestClient(small_app) as client:
        chunks = iter([b'--abc\r\nContent-Disposition: form-data; name="file"; filename="a.kml"\r\n\r\n', b"x" * 200, b"\r\n--abc--\r\n"])
        result = client.post("/", content=chunks, headers={"Content-Type": "multipart/form-data; boundary=abc"})
        assert result.status_code == 413
        assert result.json()["error"]["code"] == "FILE_TOO_LARGE"
