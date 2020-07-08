#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 05-Jun-2020
@Filename:             service.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   07-Jul-2020
"""

import rpyc
from rpcad import RPCAD_PORT, RPCAD_FALLBACK_PORT, RPCAD_HOSTNAME
from rpcad.parameter import Parameter
from abc import abstractmethod
from typing import Dict, Union


class CADService(rpyc.Service):
    def on_connect(self, conn):
        # code that runs when a connection is created
        # (to init the service, if needed)
        pass

    def on_disconnect(self, conn):
        # code that runs after the connection has already closed
        # (to finalize the service, if needed)
        pass

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
