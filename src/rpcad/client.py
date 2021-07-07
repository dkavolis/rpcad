#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 06-Jun-2020
@Filename:             client.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   07-Jul-2021
"""

import os
from typing import Dict, Union, Any, overload, Iterable, Callable

from rpcad.common import BaseClient
from rpcad.parameter import Parameter
from rpcad.commands import Command, PhysicalProperty, Accuracy

from functools import wraps


def remote_call(f: Callable):
    @wraps(f)
    def wrapper(self: "BaseClient", *args, **kwargs):
        return getattr(self.connection.root, f.__name__)(*args, **kwargs)

    return wrapper


class Client(BaseClient):
    @remote_call
    def parameter(self, name: str) -> Parameter:  # type: ignore
        pass

    @remote_call
    def parameters(self) -> Dict[str, Parameter]:  # type: ignore
        pass

    def open_project(self, path: str) -> None:
        return self.connection.root.open_project(path=os.path.abspath(path))

    @remote_call
    def save_project(self) -> None:
        pass

    @remote_call
    def close_project(self) -> None:
        pass

    def export_project(self, path: str, *args, **kwargs) -> None:
        return self.connection.root.export_project(
            path=os.path.abspath(path), *args, **kwargs
        )

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
    def physical_properties(self, prop, part, accuracy):  # type: ignore
        pass

    @overload
    def batch_commands(self, commands: Command) -> Any:
        ...

    @overload
    def batch_commands(self, commands: Iterable[Command]) -> list:
        ...

    @remote_call
    def batch_commands(self, commands):  # type: ignore
        pass
