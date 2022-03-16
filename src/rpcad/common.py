#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations

import os
from types import TracebackType
import rpyc
from typing import TYPE_CHECKING, Type, TypeVar, Union

RPCAD_HOSTNAME = os.environ.get("RPCAD_HOSTNAME", "localhost")
RPCAD_PORT = os.environ.get("RPCAD_PORT", 18_888)
RPCAD_FALLBACK_PORT = os.environ.get("RPCAD_FALLBACK_PORT", 18_898)
RPCAD_LOGDIR = os.environ.get(
    "RPCAD_LOGDIR", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
RPCAD_LOGLEVEL = os.environ.get("RPCAD_LOGLEVEL", "DEBUG")

if TYPE_CHECKING:
    from rpyc import Connection

Client = TypeVar("Client", bound="BaseClient")


class BaseClient:
    def __init__(
        self, hostname: str = RPCAD_HOSTNAME, port: Union[int, str] = RPCAD_PORT
    ):
        self.connection: "Connection"
        config = {"allow_public_attrs": True, "allow_safe_attrs": True}
        try:
            self.connection = rpyc.connect(hostname, port, config=config)
        except BaseException:
            self.connection = rpyc.connect(hostname, RPCAD_FALLBACK_PORT, config=config)

    def __enter__(self: Client) -> Client:
        return self

    def __exit__(
        self, type: Type[Exception], value: Exception, traceback: TracebackType
    ) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()


del os
del Client
