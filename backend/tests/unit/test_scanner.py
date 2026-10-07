import io
from unittest.mock import MagicMock, patch
import pytest
from app.services.malware_scan_service import MalwareScanService
from app.core.exceptions import AppError


@pytest.mark.parametrize("reply,code", [(b"stream: OK\0", None), (b"stream: Eicar-Signature FOUND\0", "MALWARE_DETECTED"), (b"stream: Heuristics.Limits.Exceeded.MaxFileSize FOUND\0", "SCAN_ERROR"), (b"INSTREAM size limit exceeded. ERROR\0", "SCAN_ERROR"), (b"", "SCAN_ERROR"), (b"unknown", "SCAN_ERROR")])
def test_stream_protocol(settings, reply, code):
    socket = MagicMock()
    socket.recv.side_effect = [reply, b""]
    with patch("socket.create_connection") as connect:
        connect.return_value.__enter__.return_value = socket
        if code:
            with pytest.raises(AppError) as exc:
                MalwareScanService(settings).scan(io.BytesIO(b"abc"))
            assert exc.value.code == code
        else:
            MalwareScanService(settings).scan(io.BytesIO(b"abc"))
        payloads = [call.args[0] for call in socket.sendall.call_args_list]
        assert payloads == [b"zINSTREAM\0", b"\x00\x00\x00\x03abc", b"\x00\x00\x00\x00"]


def test_unavailable_fails_closed(settings):
    with patch("socket.create_connection", side_effect=OSError("private scanner hostname")):
        with pytest.raises(AppError) as exc:
            MalwareScanService(settings).scan(io.BytesIO(b"abc"))
    assert exc.value.code == "SCAN_ERROR"
    assert "private" not in str(exc.value)
