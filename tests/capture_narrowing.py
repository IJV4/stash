from capture_rig import CaptureRig

from stash.capture import Deferred, Filed, IncomingMessage


def handle_filed(rig: CaptureRig, message: IncomingMessage) -> Filed:
    result = rig.pipeline.handle(message)
    if not isinstance(result, Filed):
        raise AssertionError(f"expected Filed, got {result!r}")
    return result


def handle_deferred(rig: CaptureRig, message: IncomingMessage) -> Deferred:
    result = rig.pipeline.handle(message)
    if not isinstance(result, Deferred):
        raise AssertionError(f"expected Deferred, got {result!r}")
    return result
