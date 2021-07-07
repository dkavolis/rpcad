#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 05-Jun-2020
@Filename:             service.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   07-Jul-2021
"""

import logging
from abc import abstractmethod
from logging import handlers
from typing import Dict, Union, Type, Iterable, Any, overload, TYPE_CHECKING
import inspect

import rpyc
from rpcad.common import (
    RPCAD_FALLBACK_PORT,
    RPCAD_HOSTNAME,
    RPCAD_LOGDIR,
    RPCAD_LOGLEVEL,
    RPCAD_PORT,
)
from rpcad.parameter import Parameter
from rpyc.utils.server import Server, ThreadedServer
from rpcad.commands import Command, PhysicalProperty, Accuracy

if TYPE_CHECKING:
    from rpyc.core.protocol import Connection

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
    def on_connect(self, conn: "Connection"):
        # code that runs when a connection is created
        # (to init the service, if needed)
        self.handler = setup_service_logger(self.__class__.__name__)
        logger.info("Service starting: %s", self.__class__.__name__)

    def on_disconnect(self, conn: "Connection"):
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

    @abstractmethod
    def _undo(self, count: int) -> None:
        pass

    @abstractmethod
    def _reload(self) -> None:
        pass

    @abstractmethod
    def _debug(self) -> None:
        pass

    @abstractmethod
    def _physical_properties(
        self, properties: Iterable[PhysicalProperty], part: str, accuracy: Accuracy
    ) -> Dict[PhysicalProperty, Any]:
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
            self._set_parameter(name, expression)

    def exposed_undo(self, count: int = 1) -> None:
        self._undo(count)

    def exposed_reload(self) -> None:
        self._reload()

    def exposed_debug(self) -> None:
        self._debug()

    @overload
    def exposed_physical_properties(
        self, prop: PhysicalProperty, part: str, accuracy: Accuracy
    ) -> Any:
        ...

    @overload
    def exposed_physical_properties(
        self, prop: Iterable[PhysicalProperty], part: str, accuracy: Accuracy
    ) -> Dict[PhysicalProperty, Any]:
        ...

    def exposed_physical_properties(self, prop, part, accuracy):
        if isinstance(prop, PhysicalProperty):
            return self._physical_properties([prop], part, accuracy)[prop]

        return self._physical_properties(prop, part, accuracy)

    def _invoke_static(self, attr, *args, **kwargs):
        if isinstance(attr, staticmethod):
            return attr.__get__(type(self))(*args, **kwargs)

        if isinstance(attr, classmethod):
            return attr.__get__(self)(*args, **kwargs)

        if inspect.isfunction(attr):
            return attr(self, *args, **kwargs)

        if inspect.ismethod(attr):
            return attr(*args, **kwargs)

        if isinstance(attr, property):
            return attr.fget(self)  # type: ignore

        # only possibility is attr is a regular attribute
        return attr

    def _find_attribute(self, name: str):
        impl_name = f"_{name}"

        # prefer implementation methods, getattr_static allows checking if
        # attributes are static and class methods
        attr = inspect.getattr_static(self, impl_name, None)
        if attr is not None:
            return attr

        # unless they don't exist
        public_name = f"exposed_{name}"
        attr = inspect.getattr_static(self, public_name, None)
        if attr is not None:
            return attr

        attr = getattr(self, impl_name, None)
        if attr is not None:
            return attr

        attr = getattr(self, public_name, None)
        if attr is not None:
            return attr

        return None

    def _execute_batch(self, commands: Iterable[Command]) -> list:
        commands = list(commands)

        # first validate that commands exist to avoid any long running code
        # before the inevitable crash
        invalid_commands = []
        resolved = []
        for command in commands:
            attr = self._find_attribute(command.name)

            if attr is None:
                invalid_commands.append(command.name)
            else:
                resolved.append(attr)

        if invalid_commands:
            raise ValueError(f"Found invalid commands: {invalid_commands}")

        results = []
        for command, function in zip(commands, resolved):
            results.append(
                self._invoke_static(function, *command.args, **command.kwargs)
            )

        return results

    @overload
    def exposed_batch_commands(self, commands: Command) -> Any:
        ...

    @overload
    def exposed_batch_commands(self, commands: Iterable[Command]) -> list:
        ...

    def exposed_batch_commands(self, commands):
        if isinstance(commands, Command):
            return self._execute_batch([commands])[0]

        return self._execute_batch(commands)

    @classmethod
    def create_server(
        cls,
        *args,
        hostname: str = RPCAD_HOSTNAME,
        port: Union[str, int] = RPCAD_PORT,
        server: Type[Server] = ThreadedServer,
        **kwargs,
    ) -> Server:

        kwargs["protocol_config"] = {"allow_public_attrs": True}

        try:
            return server(cls, *args, port=port, **kwargs)
        except OSError:
            return server(cls, *args, port=RPCAD_FALLBACK_PORT, **kwargs)
