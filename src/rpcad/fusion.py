#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
@Author:               Daumantas Kavolis <dkavolis>
@Date:                 05-Jun-2020
@Filename:             fusion.py
@Last Modified By:     Daumantas Kavolis
@Last Modified Time:   14-Jul-2020
"""

import logging
import os
from typing import Dict, Optional, Union

from rpcad.parameter import Parameter
from rpcad.service import CADService

import adsk.core
import adsk.fusion

logger = logging.getLogger(__name__)


class Fusion360Service(CADService):
    def _setup(self) -> None:
        # setup fusion 360 objects
        self._app = adsk.core.Application.get()
        self._document: Optional[adsk.core.Document] = self._app.activeDocument
        self._design: Optional[adsk.fusion.Design] = adsk.fusion.Design.cast(
            self._app.activeProduct
        )

        ui = self._app.userInterface
        self._undo_command = ui.commandDefinitions.itemById("UndoCommand")

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
        else:
            raise ValueError(f"Invalid extension {extension}")

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
        """
        Use kwargs to pass additional export values

        stl:
            body: str
                name of the body to export
            https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-64f3e0ab-f3bc-445e-9505-7dba9d296ebd
        """

        if self._design is None:
            raise RuntimeError("No open documents")

        os.makedirs(os.path.dirname(path), exist_ok=True)

        # create a single exportManager instance
        export_manager = self._design.exportManager

        extension = os.path.splitext(path)[1]

        if extension == ".stl":
            body = self._design.rootComponent
            body_name = kwargs.pop("body", None)
            if body_name is not None:
                bodies = self._design.rootComponent.meshBodies
                body = bodies.item(0)
                for i in range(bodies.count):
                    if bodies.item(i).name == body_name:
                        body = bodies.item(i)
                        break

            options = export_manager.createSTLExportOptions(body, path)
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
        else:
            raise ValueError(f"Invalid extension {extension}")

        for attr, value in kwargs.items():
            setattr(options, attr, value)

        export_manager.execute(options)

    def _set_parameter(self, name: str, parameter: Union[str, float]) -> None:
        if self._design is None:
            raise RuntimeError("No open projects")

        param = self._design.allParameters.itemByName(name)
        if param is None:
            raise ValueError(f"Invalid parameter name {name}")

        try:
            if isinstance(parameter, str):
                param.expression = str(parameter)
            else:
                param.value = float(parameter)
        except TypeError:
            logger.exception(
                "Failed setting '%s' to '%s'(%s)", name, parameter, type(parameter)
            )
            raise

        logger.debug("Set parameter %s = %s (%s)", name, param.expression, parameter)

    def _undo(self, count: int):
        if self._design is None or self._undo_command is None:
            raise RuntimeError("No open projects")

        for _ in range(count):
            if not self._undo_command.execute():
                break

    def _reload(self):
        if self._document is None:
            raise RuntimeError("No open projects")

        data_file = self._document.dataFile
        self._document.close(False)
        self._document = self._app.documents.open(data_file)

    def _debug(self):
        self.app = self._app
        self.document = self._document
        self.design = self._design
        self.undo_command = self._undo_command


def cast(parameter: adsk.fusion.Parameter) -> Parameter:
    return Parameter(value=parameter.value, expression=parameter.expression)
