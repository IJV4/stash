import logging
from collections.abc import Iterator
from contextlib import contextmanager


class LogRecorder(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    def entries(self) -> list[tuple[int, str]]:
        return [(record.levelno, record.getMessage()) for record in self.records]


@contextmanager
def recording_logs(logger_name: str) -> Iterator[LogRecorder]:
    logger = logging.getLogger(logger_name)
    recorder = LogRecorder()
    previous_level = logger.level
    logger.addHandler(recorder)
    logger.setLevel(logging.DEBUG)
    try:
        yield recorder
    finally:
        logger.removeHandler(recorder)
        logger.setLevel(previous_level)
