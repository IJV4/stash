import threading
from collections.abc import Callable
from concurrent.futures import Future
from functools import partial
from typing import TypeVar

T = TypeVar("T")

THREAD_TIMEOUT_SECONDS = 5


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
