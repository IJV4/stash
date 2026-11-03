import logging
import math
import threading
from concurrent.futures import Future, wait

from stash.domain import http_url_host
from stash.enrich.links import LinkInfo, LinkInspector

logger = logging.getLogger(__name__)


class DeadlineInspector:
    def __init__(self, inner: LinkInspector, deadline_seconds: float) -> None:
        if not math.isfinite(deadline_seconds) or deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be a positive, finite number")
        self._inner = inner
        self._deadline_seconds = deadline_seconds

    def inspect(self, url: str) -> LinkInfo:
        outcome: Future[LinkInfo] = Future()
        threading.Thread(target=self._run, args=(url, outcome), daemon=True).start()
        done, _ = wait([outcome], timeout=self._deadline_seconds)
        if not done:
            logger.warning(
                "link inspection gave up after %s seconds: host %s",
                self._deadline_seconds,
                http_url_host(url),
            )
            return LinkInfo.unknown(url)
        return outcome.result()

    def _run(self, url: str, outcome: Future[LinkInfo]) -> None:
        try:
            outcome.set_result(self._inner.inspect(url))
        except BaseException as error:
            outcome.set_exception(error)
