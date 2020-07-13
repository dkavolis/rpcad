#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 06-Jun-2020
@Filename:             client.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   13-Jul-2020
"""

import os
from typing import Dict, Union

import rpyc
from rpcad.common import RPCAD_FALLBACK_PORT, RPCAD_HOSTNAME, RPCAD_PORT
from rpcad.parameter import Parameter


class Client:
    def __init__(self, hostname: str = RPCAD_HOSTNAME, port: int = RPCAD_PORT):
        config = {"allow_public_attrs": True}
        try:
            self.connection = rpyc.connect(hostname, port, config=config)
        except:  # noqa: E722
            self.connection = rpyc.connect(hostname, RPCAD_FALLBACK_PORT, config=config)

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, type, value, traceback) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    def parameter(self, name: str) -> Parameter:
        return self.connection.root.parameter(name)

    def parameters(self) -> Dict[str, Parameter]:
        return self.connection.root.parameters()

    def open_project(self, path: str) -> None:
        return self.connection.root.open_project(os.path.abspath(path))

    def save_project(self) -> None:
        return self.connection.root.save_project()

    def close_project(self) -> None:
        return self.connection.root.close_project()

    def export_project(self, path: str, *args, **kwargs) -> None:
        return self.connection.root.export_project(
            os.path.abspath(path), *args, **kwargs
        )

    def set_parameter(self, name: str, expression: Union[str, float]) -> None:
        return self.connection.root.set_parameter(name, expression)

    def set_parameters(self, parameters: Dict[str, Union[str, float]]) -> None:
        return self.connection.root.set_parameters(parameters)
