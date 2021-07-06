#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os
import rpyc
from typing import TypeVar, Union

RPCAD_HOSTNAME = os.environ.get("RPCAD_HOSTNAME", "localhost")
RPCAD_PORT = os.environ.get("RPCAD_PORT", 18_888)
RPCAD_FALLBACK_PORT = os.environ.get("RPCAD_FALLBACK_PORT", 18_898)
RPCAD_LOGDIR = os.environ.get(
    "RPCAD_LOGDIR", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
RPCAD_LOGLEVEL = os.environ.get("RPCAD_LOGLEVEL", "DEBUG")


Client = TypeVar("Client", bound="BaseClient")


class BaseClient:
    def __init__(
        self, hostname: str = RPCAD_HOSTNAME, port: Union[int, str] = RPCAD_PORT
    ):
        config = {"allow_public_attrs": True}
        try:
            self.connection = rpyc.connect(hostname, port, config=config)  # noqa: F821
        except BaseException:
            self.connection = rpyc.connect(  # noqa: F821
                hostname, RPCAD_FALLBACK_PORT, config=config
            )

    def __enter__(self: Client) -> Client:
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()


del os
del rpyc
del Client
