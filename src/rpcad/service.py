#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 05-Jun-2020
@Filename:             service.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   09-Jul-2020
"""

import logging
from abc import abstractmethod
from logging import handlers
from typing import Dict, Union

import rpyc
from rpcad.common import (
    RPCAD_FALLBACK_PORT,
    RPCAD_HOSTNAME,
    RPCAD_LOGDIR,
    RPCAD_LOGLEVEL,
    RPCAD_PORT,
)
from rpcad.parameter import Parameter

logger = logging.getLogger(__name__)


def setup_service_logger(service_name: str) -> logging.Handler:
    import os

    logger = logging.getLogger("rpcad")
    logger.setLevel(getattr(logging, RPCAD_LOGLEVEL, logging.DEBUG))
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logdir = os.path.abspath(RPCAD_LOGDIR)
    logHandler = handlers.RotatingFileHandler(
        os.path.join(logdir, f"{service_name}.log"),
        mode="a+",
        backupCount=5,
        delay=True,
    )
    logHandler.setFormatter(formatter)
    logHandler.flush()
    logger.addHandler(logHandler)
    logger.info("Log level is set to %s", logger.getEffectiveLevel())

    return logHandler


def finish_service_logger(handler: logging.Handler) -> None:
    if handler is None:
        return

    logger = logging.getLogger("rpcad")
    logger.removeHandler(handler)


class CADService(rpyc.Service):
    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        self.handler = setup_service_logger(self.__class__.__name__)
        logger.info("Service starting: %s", self.__class__.__name__)

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        if self.handler is not None:
            self.handler.flush()
            finish_service_logger(self.handler)

    # abstract methods to be implemented by specific service
    @abstractmethod
    def _get_parameter(self, name: str) -> Parameter:
        pass

    @abstractmethod
    def _get_all_parameters(self) -> Dict[str, Parameter]:
        pass

    @abstractmethod
    def _open_project(self, path: str) -> None:
        pass

    @abstractmethod
    def _save_project(self) -> None:
        pass

    @abstractmethod
    def _close_project(self) -> None:
        pass

    @abstractmethod
    def _export_project(self, path: str, *args, **kwargs) -> None:
        pass

    @abstractmethod
    def _set_parameter(self, name: str, parameter: Union[str, float]) -> None:
        pass

    # expose service methods
    def exposed_parameter(self, name: str) -> Parameter:
        return self._get_parameter(name)

    def exposed_parameters(self) -> Dict[str, Parameter]:
        return self._get_all_parameters()

    def exposed_open_project(self, path: str) -> None:
        self._open_project(path)

    def exposed_save_project(self) -> None:
        self._save_project()

    def exposed_close_project(self) -> None:
        self._close_project()

    def exposed_export_project(self, path: str, *args, **kwargs) -> None:
        self._export_project(path, *args, **kwargs)

    def exposed_set_parameter(self, name: str, expression: Union[str, float]) -> None:
        self._set_parameter(name, expression)

    def exposed_set_parameters(self, parameters: Dict[str, Union[str, float]]) -> None:
        for name, expression in parameters.items():
            # for weird reasons dict key is Tuple[str]...
            if isinstance(name, tuple) and len(name) == 1:
                name = name[0]
            self._set_parameter(name, expression)

    @classmethod
    def create_server(
        cls, *args, hostname=RPCAD_HOSTNAME, port=RPCAD_PORT, **kwargs
    ) -> rpyc.ThreadedServer:
        from rpyc.utils.server import ThreadedServer

        kwargs["protocol_config"] = {"allow_public_attrs": True}

        try:
            return ThreadedServer(cls, *args, port=port, **kwargs)
        except OSError:
            return ThreadedServer(cls, *args, port=RPCAD_FALLBACK_PORT, **kwargs)
