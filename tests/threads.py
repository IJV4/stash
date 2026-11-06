import threading
from collections.abc import Callable
from concurrent.futures import Future
from functools import partial
from typing import TypeVar

T = TypeVar("T")

THREAD_TIMEOUT_SECONDS = 5
WAIT_LIMIT_SECONDS = 1.0
OVERLAP_GRACE_SECONDS = 0.005


class OverlapGate:
    def __init__(self) -> None:
        self.release = threading.Event()
        self.entered = threading.Event()
        self.overlapped = threading.Event()
        self.max_inside = 0
        self._inside = 0
        self._counting = threading.Lock()

    def hold(self) -> None:
        with self._counting:
            self._inside += 1
            self.max_inside = max(self.max_inside, self._inside)
            if self._inside > 1:
                self.overlapped.set()
        self.entered.set()
        self.release.wait(WAIT_LIMIT_SECONDS)
        with self._counting:
            self._inside -= 1


def run_in_thread(action: Callable[[], T], timeout: float = THREAD_TIMEOUT_SECONDS) -> T:
    return _settled(_spawn(action), timeout).result()


def run_concurrently(
    workers: int, action: Callable[[int], None], timeout: float = THREAD_TIMEOUT_SECONDS
) -> list[BaseException]:
    start = threading.Barrier(workers)

    def run(worker: int) -> None:
        start.wait(timeout)
        action(worker)

    futures = [_spawn(partial(run, worker)) for worker in range(workers)]
    outcomes = [_settled(future, timeout).exception() for future in futures]
    return [error for error in outcomes if error is not None]


def start(action: Callable[[], object]) -> threading.Thread:
    thread = threading.Thread(target=action, daemon=True)
    thread.start()
    return thread


def start_announcing(announce: threading.Event, action: Callable[[], object]) -> threading.Thread:
    def announce_then_act() -> None:
        announce.set()
        action()

    return start(announce_then_act)


def await_signal(signal: threading.Event) -> None:
    if not signal.wait(WAIT_LIMIT_SECONDS):
        raise AssertionError("the signal never came")


def _spawn(action: Callable[[], T]) -> Future[T]:
    future: Future[T] = Future()

    def run() -> None:
        try:
            future.set_result(action())
        except BaseException as error:
            future.set_exception(error)

    threading.Thread(target=run, daemon=True).start()
    return future


def _settled(future: Future[T], timeout: float) -> Future[T]:
    try:
        future.exception(timeout)
    except TimeoutError as error:
        raise AssertionError("worker did not finish") from error
    return future
