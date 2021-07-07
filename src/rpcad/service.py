#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 05-Jun-2020
@Filename:             service.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   07-Jul-2021
"""

from abc import abstractmethod
from typing import Dict, Union, Type, Iterable, Any, overload
import inspect

import rpyc
from rpcad.common import (
    RPCAD_FALLBACK_PORT,
    RPCAD_HOSTNAME,
    RPCAD_PORT,
)
from rpcad.parameter import Parameter
from rpyc.utils.server import Server, ThreadedServer
from rpcad.commands import Command, PhysicalProperty, Accuracy


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
    def _export_project(self, path: str, *args, **kwargs) -> None:
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

    def exposed_export_project(self, path: str, *args, **kwargs) -> None:
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
