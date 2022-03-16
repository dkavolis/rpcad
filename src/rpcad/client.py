#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations

import os
from typing import (
    TYPE_CHECKING,
    TypeVar,
    Union,
    Any,
    Iterable,
    Callable,
    Dict,
    List,
)
from typing import overload
import inspect

from rpcad.common import BaseClient
from rpcad.parameter import Parameter
from rpcad.commands import Command, PhysicalProperty, Accuracy

from functools import wraps

if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec, Literal

    P = ParamSpec("P")

R = TypeVar("R")

# ParamSpec is still limited so there will be a lot of type: ignore comments to shut up
# mypy, also mypy seems to have other issues with ParamSpec still


def remote_call(f: Callable[Concatenate["BaseClient", P], R]):  # type: ignore
    # ParamSpec cannot yet be concatenated with keyword-only arguments so rely on
    # language server inferring the return type from the remaining type hints

    signature = inspect.signature(f)

    # pyright: reportGeneralTypeIssues=false

    # complains about keyword-only argument after ParamSpec.args
    # mypy doesn't like ParamSpec, even in 3.10
    @overload
    def wrapper(
        self: BaseClient,
        *args: P.args,  # type: ignore
        as_command: Literal[True] = ...,
        **kwargs: P.kwargs  # type: ignore
    ) -> Command[R]:
        ...

    @overload
    def wrapper(
        self: BaseClient,
        *args: P.args,  # type: ignore
        as_command: Literal[False] = ...,
        **kwargs: P.kwargs  # type: ignore
    ) -> R:
        ...

    @wraps(f)
    def wrapper(
        self: BaseClient,
        *args: P.args,  # type: ignore
        as_command: bool = False,
        **kwargs: P.kwargs  # type: ignore
    ) -> Union[Command[R], R]:
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
            command: Command[R] = Command(name=f.__name__)
            command.args = arguments.args[1:]
            command.kwargs = arguments.kwargs
            return command

        return getattr(self.connection.root, f.__name__)(  # type: ignore # unknown root
            *arguments.args[1:], **arguments.kwargs
        )

    return wrapper


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
    def export_project(self, path: str, *args: Any, **kwargs: Any) -> None:
        pass

    @remote_call
    def set_parameters(self, **kwargs: Union[str, float]) -> None:
        pass

    @remote_call
    def undo(self, count: int = 1) -> None:
        return self.open_project(path=count, other=1)

    @remote_call
    def reload(self) -> None:
        pass

    @remote_call
    def debug(self) -> None:
        pass

    @overload
    @remote_call
    def physical_properties(
        self, prop: PhysicalProperty, part: str, accuracy: Accuracy
    ) -> Any:
        ...

    @overload
    @remote_call
    def physical_properties(
        self, prop: Iterable[PhysicalProperty], part: str, accuracy: Accuracy
    ) -> Dict[PhysicalProperty, Any]:
        ...

    @remote_call
    def physical_properties(
        self,
        prop: Union[PhysicalProperty, Iterable[PhysicalProperty]],
        part: str,
        accuracy: Accuracy = Accuracy.Medium,
    ) -> Union[Any, Dict[str, Any]]:
        pass

    @overload
    def batch_commands(self, commands: Command[R]) -> R:
        ...

    @overload
    def batch_commands(self, commands: Iterable[Command[R]]) -> List[R]:
        ...

    def batch_commands(
        self, commands: Union[Command[R], Iterable[Command[R]]]
    ) -> Union[R, List[R]]:
        return self.connection.root.batch_commands(commands)  # type: ignore
