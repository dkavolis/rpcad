#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 06-Jun-2020
@Filename:             client.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   22-Jul-2021
"""

import os
from typing import Dict, Union, Any, Iterable, Callable
from typing import overload as _overload
import inspect

from rpcad.common import BaseClient
from rpcad.parameter import Parameter
from rpcad.commands import Command, PhysicalProperty, Accuracy

from functools import wraps


def remote_call(f: Callable):
    signature = inspect.signature(f)

    @wraps(f)
    def wrapper(self: "BaseClient", *args, as_command: bool = False, **kwargs):
        arguments = signature.bind(self, *args, **kwargs)
        arguments.apply_defaults()

        # special handling for path arguments, should probably add a handler mapping as
        # decorator argument instead
        path = arguments.arguments.get("path", None)
        if path is not None:
            arguments.arguments["path"] = os.path.abspath(path)

        if as_command:
            # name may be one of the kwargs so set args and kwargs outside the
            # constructor
            command = Command(name=f.__name__)
            command.args = arguments.args[1:]
            command.kwargs = arguments.kwargs
            return command

        return getattr(self.connection.root, f.__name__)(
            *arguments.args[1:], **arguments.kwargs
        )

    return wrapper


def overload(f: Callable):
    return _overload(remote_call(f))


class Client(BaseClient):
    @remote_call
    def parameter(self, name: str) -> Parameter:  # type: ignore
        pass

    @remote_call
    def parameters(self) -> Dict[str, Parameter]:  # type: ignore
        pass

    @remote_call
    def open_project(self, path: str) -> None:
        pass

    @remote_call
    def save_project(self) -> None:
        pass

    @remote_call
    def close_project(self) -> None:
        pass

    @remote_call
    def export_project(self, path: str, *args, **kwargs) -> None:
        pass

    @remote_call
    def set_parameters(self, **kwargs: Union[str, float]) -> None:
        pass

    @remote_call
    def undo(self, count: int = 1) -> None:
        pass

    @remote_call
    def reload(self) -> None:
        pass

    @remote_call
    def debug(self) -> None:
        pass

    @overload
    def physical_properties(
        self, prop: PhysicalProperty, part: str, accuracy: Accuracy
    ) -> Any:
        ...

    @overload
    def physical_properties(
        self, prop: Iterable[PhysicalProperty], part: str, accuracy: Accuracy
    ) -> Dict[PhysicalProperty, Any]:
        ...

    @remote_call
    def physical_properties(self, prop, part, accuracy=Accuracy.Medium):  # type: ignore
        pass

    @_overload
    def batch_commands(self, commands: Command) -> Any:
        ...

    @_overload
    def batch_commands(self, commands: Iterable[Command]) -> list:
        ...

    @remote_call
    def batch_commands(self, commands):  # type: ignore
        pass
