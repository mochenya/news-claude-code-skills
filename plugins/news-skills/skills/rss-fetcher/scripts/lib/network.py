from __future__ import annotations

import socket

DEFAULT_NETWORK_TIMEOUT_SECONDS = 20


def configure_network_timeout(timeout_seconds: int = DEFAULT_NETWORK_TIMEOUT_SECONDS) -> None:
    socket.setdefaulttimeout(timeout_seconds)
