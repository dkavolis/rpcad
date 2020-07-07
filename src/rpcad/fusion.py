#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 05-Jun-2020
@Filename:             fusion.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   07-Jul-2020
"""

from rpcad.service import CADService
from rpcad.parameter import Parameter
from typing import Dict, Union, Optional

import os

import adsk.core
import adsk.fusion


class Fusion360Service(CADService):
    def _setup(self) -> None:
        # setup fusion 360 objects
        self._app = adsk.core.Application.get()
        self._document: Optional[adsk.core.Document] = self._app.activeDocument
        self._design: Optional[adsk.fusion.Design] = adsk.fusion.Design.cast(
            self._app.activeProduct
        )

    def on_connect(self, conn):
        super().on_connect(conn)
        self._setup()

    def on_disconnect(self, conn):
        super().on_disconnect(conn)
        self._app = None
        self._design = None

    def _get_parameter(self, name: str) -> Parameter:
        if self._design is None:
            raise RuntimeError("No open projects")
        params = self._design.allParameters
        return cast(params.itemByName(name))

    def _get_all_parameters(self) -> Dict[str, Parameter]:
        if self._design is None:
            raise RuntimeError("No open projects")
        items = {}
        for parameter in self._design.allParameters:
            items[parameter.name] = cast(parameter)
        return items

    def _open_project(self, path: str) -> None:
        import_manager = self._app.importManager

        extension = os.path.splitext(path)[1]

        if extension == ".step":
            options = import_manager.createSTEPImportOptions(path)
        elif extension == ".smt":
            options = import_manager.createSMTImportOptions(path)
        elif extension == ".sat":
            options = import_manager.createSATImportOptions(path)
        elif extension == ".iges":
            options = import_manager.createIGESImportOptions(path)
        elif extension == ".f3d":
            options = import_manager.createFusionArchiveImportOptions(path)

        self._document = import_manager.importToNewDocument(options)

        if self._document is None:
            raise ValueError(f"Could not open project '{path!s}'")

        self._document.activate()
        self._design = adsk.fusion.Design.cast(self._app.activeProduct)

    def _save_project(self) -> None:
        if self._document is None:
            raise RuntimeError("No open documents")

        self._document.save("Saved from an RPC service")

    def _close_project(self) -> None:
        if self._document is None:
            raise RuntimeError("No open documents")
        self._document.close(False)
        self._document = None
        self._design = None

    def _export_project(self, path: str, *args, **kwargs) -> None:
        if self._design is None:
            raise RuntimeError("No open documents")

        os.makedirs(os.path.dirname(path), exist_ok=True)

        # create a single exportManager instance
        export_manager = self._design.exportManager

        extension = os.path.splitext(path)[1]

        if extension == ".stl":
            root = self._design.rootComponent
            options = export_manager.createSTLExportOptions(root, path)
        elif extension == ".step":
            options = export_manager.createSTEPExportOptions(path)
        elif extension == ".smt":
            options = export_manager.createSMTExportOptions(path)
        elif extension == ".sat":
            options = export_manager.createSATExportOptions(path)
        elif extension == ".iges":
            options = export_manager.createIGESExportOptions(path)
        elif extension == ".f3d":
            options = export_manager.createFusionArchiveExportOptions(path)

        export_manager.execute(options)

    def _set_parameter(self, name: str, parameter: Union[str, float]) -> None:
        if self._design is None:
            raise RuntimeError("No open projects")

        param = self._design.allParameters.itemByName(name)
        if isinstance(parameter, str):
            param.expression = parameter
        else:
            param.value = parameter


def cast(parameter: adsk.fusion.Parameter) -> Parameter:
    return Parameter(value=parameter.value, expression=parameter.expression)
