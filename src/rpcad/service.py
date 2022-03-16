#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations

from abc import abstractmethod
from typing import TypeVar, Union, Type, Iterable, Any, overload, Dict, List
import inspect
import logging

import rpyc
from rpyc.utils.server import Server, ThreadedServer

from rpcad.common import (
    RPCAD_FALLBACK_PORT,
    RPCAD_HOSTNAME,
    RPCAD_PORT,
)
from rpcad.parameter import Parameter
from rpcad.commands import Command, PhysicalProperty, Accuracy

logger = logging.getLogger(__name__)


R = TypeVar("R")


class CADService(rpyc.Service):
    # abstract methods to be implemented by specific service
    @abstractmethod
    def _parameter(self, name: str) -> Parameter:
        pass

    @abstractmethod
    def _parameters(self) -> Dict[str, Parameter]:
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
    def _export_project(self, path: str, *args: Any, **kwargs: Any) -> None:
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
    def _set_parameters(self, parameters: Dict[str, Union[str, float]]) -> None:
        pass

    @abstractmethod
    def _physical_properties(
        self, properties: Iterable[PhysicalProperty], part: str, accuracy: Accuracy
    ) -> Dict[PhysicalProperty, Any]:
        pass

    # expose service methods
    def exposed_parameter(self, name: str) -> Parameter:
        return self._parameter(name)

    def exposed_parameters(self) -> Dict[str, Parameter]:
        return self._parameters()

    def exposed_open_project(self, path: str) -> None:
        self._open_project(path)

    def exposed_save_project(self) -> None:
        self._save_project()

    def exposed_close_project(self) -> None:
        self._close_project()

    def exposed_export_project(self, path: str, *args: Any, **kwargs: Any) -> None:
        self._export_project(path, *args, **kwargs)

    def exposed_set_parameters(self, **kwargs: Union[str, float]) -> None:
        self._set_parameters(kwargs)

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

    def exposed_physical_properties(
        self,
        prop: Union[PhysicalProperty, Iterable[PhysicalProperty]],
        part: str,
        accuracy: Accuracy,
    ) -> Union[Any, Dict[PhysicalProperty, Any]]:
        if isinstance(prop, PhysicalProperty):
            return self._physical_properties([prop], part, accuracy)[
                PhysicalProperty(prop.value)
            ]

        return self._physical_properties(prop, part, accuracy)

    def _invoke_static(self, attr: Any, *args: Any, **kwargs: Any) -> Any:
        try:
            if isinstance(attr, staticmethod):
                return attr.__get__(type(self))(*args, **kwargs)  # type: ignore

            if isinstance(attr, classmethod):
                return attr.__get__(self)(*args, **kwargs)  # type: ignore

            if inspect.isfunction(attr):
                return attr(self, *args, **kwargs)

            if inspect.ismethod(attr):
                return attr(*args, **kwargs)

            if isinstance(attr, property):
                return attr.fget(self)  # type: ignore
        except Exception:
            logger.error(
                "Error _invoke_static(self=%s, attr=%s, *args=%s, **kwargs=%s)",
                self,
                attr,  # type: ignore
                args,
                kwargs,
            )
            raise

        # only possibility is attr is a regular attribute
        return attr

    def _find_attribute(self, name: str):
        exposed = f"exposed_{name}"

        attr = inspect.getattr_static(self, exposed, None)
        if attr is not None:
            return attr

        return getattr(self, exposed, None)

    def _execute_batch(self, commands: Iterable[Command[R]]) -> List[R]:
        commands = list(commands)

        # first validate that commands exist to avoid any long running code
        # before the inevitable crash
        invalid_commands: List[str] = []
        resolved: List[Any] = []
        for command in commands:
            attr = self._find_attribute(command.name)

            if attr is None:
                invalid_commands.append(command.name)
            else:
                resolved.append(attr)

        if invalid_commands:
            raise ValueError(f"Found invalid commands: {invalid_commands}")

        logger.debug("Batch commands received:")
        for command, function in zip(commands, resolved):
            logger.debug(
                "  %s %r (args=%s, kwargs=%s)",
                command.name,
                function,
                command.args,
                command.kwargs,
            )

        results: List[R] = []
        for command, function in zip(commands, resolved):
            results.append(
                self._invoke_static(function, *command.args, **command.kwargs)
            )

        return results

    @overload
    def exposed_batch_commands(self, commands: Command[R]) -> R:
        ...

    @overload
    def exposed_batch_commands(self, commands: Iterable[Command[R]]) -> List[R]:
        ...

    def exposed_batch_commands(
        self, commands: Union[Command[R], Iterable[Command[R]]]
    ) -> Union[R, List[R]]:
        if isinstance(commands, Command):
            return self._execute_batch([commands])[0]

        return self._execute_batch(commands)

    @classmethod
    def create_server(
        cls,
        *args: Any,
        hostname: str = RPCAD_HOSTNAME,
        port: Union[str, int] = RPCAD_PORT,
        server: Type[Server] = ThreadedServer,
        **kwargs: Any,
    ) -> Server:

        kwargs["protocol_config"] = {
            "allow_public_attrs": True,
            "allow_safe_attrs": True,
        }

        try:
            return server(cls, *args, hostname=hostname, port=port, **kwargs)
        except OSError:
            return server(
                cls, *args, hostname=hostname, port=RPCAD_FALLBACK_PORT, **kwargs
            )
