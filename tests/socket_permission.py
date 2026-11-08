import errno
import socket
from functools import cache

import pytest
from library_server_rig import ANY_FREE_PORT, LOOPBACK

BINDING_FORBIDDEN_ERRNOS = frozenset({errno.EPERM, errno.EACCES})
BINDING_FORBIDDEN_REASON = "binding a local socket is not permitted here (sandbox); runs on the PC"


@cache
def binding_is_forbidden() -> bool:
    try:
        with socket.socket() as probe:
            probe.bind((LOOPBACK, ANY_FREE_PORT))
    except PermissionError:
        return True
    except OSError as error:
        return error.errno in BINDING_FORBIDDEN_ERRNOS
    return False


requires_local_binding = pytest.mark.skipif(binding_is_forbidden(), reason=BINDING_FORBIDDEN_REASON)
