#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations

import os
from typing import (
    Callable,
    Optional,
    Union,
    TYPE_CHECKING,
    TypeVar,
    Generic,
    cast,
    overload,
    Iterable,
    Any,
    Dict,
    List,
)

from functools import wraps

from rpyc import async_

from rpcad.parameter import Parameter
from rpcad.common import BaseClient, RPCAD_HOSTNAME, RPCAD_PORT
from rpcad.commands import Command, PhysicalProperty, Accuracy

if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec
    from rpyc.core.async_ import AsyncResult as AsyncResult_
    from rpyc.utils.helpers import _Async  # type: ignore

    P = ParamSpec("P")

T = TypeVar("T")
R = TypeVar("R")


class AsyncResult(Generic[T]):

    __slots__ = ("_async_result",)

    def __init__(self, async_result: "AsyncResult_"):
        self._async_result = async_result

    def __repr__(self) -> str:
        return self._async_result.__repr__()

    def __call__(self, is_exc: bool, obj: T) -> None:
        self._async_result.__call__(is_exc=is_exc, obj=obj)

    def wait(self) -> None:
        self._async_result.wait()

    def add_callback(self, func: Callable[["AsyncResult[T]"], None]) -> None:
        def cb(r: AsyncResult_) -> None:
            assert r is self._async_result

            func(self)

        self._async_result.add_callback(cb)

    def set_expiry(self, timeout: Optional[float]) -> None:
        self._async_result.set_expiry(timeout)

    @property
    def ready(self) -> bool:
        return self._async_result.ready

    @property
    def error(self) -> bool:
        return cast(bool, self._async_result.error)

    @property
    def expired(self) -> bool:
        return self._async_result.expired  # type: ignore

    @property
    def value(self) -> T:
        return self._async_result.value  # type: ignore

    def __iter__(self) -> "AsyncResult[T]":
        return self

    def __next__(self) -> None:
        if self.ready:
            raise StopIteration

    def __await__(self) -> "AsyncResult[T]":
        return self


def remote_call(
    f: Callable[Concatenate["AsyncClient", P], R]  # type: ignore
) -> Callable[Concatenate["AsyncClient", P], AsyncResult[R]]:  # type: ignore
    @wraps(f)
    def wrapper(
        self: "AsyncClient", *args: P.args, **kwargs: P.kwargs
    ) -> AsyncResult[R]:
        return self._async(f.__name__, *args, **kwargs)  # type: ignore

    return wrapper


class AsyncClient(BaseClient):
    def __init__(
        self, hostname: str = RPCAD_HOSTNAME, port: Union[int, str] = RPCAD_PORT
    ):
        super().__init__(hostname=hostname, port=port)
        self._async_methods: Dict[str, "_Async"] = {}

    @remote_call
    def parameter(self, name: str) -> Parameter:  # type: ignore
        pass

    @remote_call
    def parameters(self) -> Dict[str, Parameter]:  # type: ignore
        pass

    def open_project(self, path: str) -> AsyncResult[None]:
        return self._async("open_project", path=os.path.abspath(path))

    @remote_call
    def save_project(self) -> None:
        pass

    @remote_call
    def close_project(self) -> None:
        pass

    def export_project(self, path: str, *args: Any, **kwargs: Any) -> AsyncResult[None]:
        return self._async(
            "export_project", path=os.path.abspath(path), *args, **kwargs
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
    def batch_commands(self, commands: Command[R]) -> R:
        ...

    @overload
    def batch_commands(self, commands: Iterable[Command[R]]) -> List[R]:
        ...

    @remote_call
    def batch_commands(
        self, commands: Union[Command[R], Iterable[Command[R]]]
    ) -> Union[R, List[R]]:  # type: ignore
        pass

    @overload
    def physical_properties(
        self, prop: PhysicalProperty, part: str, accuracy: Accuracy
    ) -> AsyncResult[Any]:
        ...

    @overload
    def physical_properties(
        self, prop: Iterable[PhysicalProperty], part: str, accuracy: Accuracy
    ) -> AsyncResult[Dict[PhysicalProperty, Any]]:
        ...

    @remote_call
    def physical_properties(self, prop, part, accuracy):  # type: ignore
        pass

    def _async(self, method_name: str, *args: Any, **kwargs: Any) -> AsyncResult[Any]:
        method: _Async
        try:
            method = self._async_methods[method_name]
        except KeyError:
            method = async_(getattr(self.connection.root, method_name))  # type: ignore
            self._async_methods[method_name] = method

        return AsyncResult(method(*args, **kwargs))
