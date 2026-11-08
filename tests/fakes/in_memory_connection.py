from io import BytesIO


class InMemoryConnection:
    def __init__(self, request: bytes) -> None:
        self._request = request
        self._response = bytearray()

    @property
    def response(self) -> bytes:
        return bytes(self._response)

    def settimeout(self, timeout: float | None) -> None:
        return None

    def makefile(self, mode: str, buffering: int = -1) -> BytesIO:
        return BytesIO(self._request)

    def sendall(self, data: bytes | memoryview) -> None:
        self._response += data
