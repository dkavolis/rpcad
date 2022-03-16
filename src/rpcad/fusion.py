#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations

import logging
import os
import pathlib
from typing import (
    TYPE_CHECKING,
    Iterable,
    Optional,
    Tuple,
    Union,
    Generic,
    TypeVar,
    Callable,
    Any,
    overload,
    Dict,
    List,
)
from abc import abstractmethod
import traceback
from logging import handlers
from threading import Event, Lock
from functools import wraps
import types
from rpyc.utils.server import Server

from rpcad.common import RPCAD_LOGDIR
from rpcad.parameter import Parameter
from rpcad.service import CADService
from rpcad.commands import PhysicalProperty, Accuracy
import adsk.cam
import adsk.core
import adsk.fusion
import adsk


if TYPE_CHECKING:
    from typing_extensions import Concatenate, ParamSpec, Literal
    from rpyc import Connection

    P = ParamSpec("P")

T = TypeVar("T")
R = TypeVar("R")

logger = logging.getLogger(__name__)


class FusionFuture(Generic[T]):
    def __init__(
        self,
        *args: Any,
        callback: Optional[Callable[[Union[T, Exception]], None]] = None,
        **kwargs: Any,
    ):
        self._result: Optional[T] = None
        self._exception: Optional[Exception] = None
        self._event = Event()

        self.args = args
        self.kwargs = kwargs
        self.callback = callback

    def set_result(self, result: T) -> None:
        self._result = result
        self._event.set()

        if self.callback is not None:
            self.callback(result)
            self.callback = None

    def set_exception(self, exception: Exception) -> None:
        self._exception = exception
        self._event.set()

        if self.callback is not None:
            self.callback(exception)

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._event.wait(timeout)

    @property
    def has_result(self) -> bool:
        return self._event.is_set() and self._result is not None

    @property
    def has_exception(self) -> bool:
        return self._event.is_set() and self._exception is not None

    @property
    def completed(self) -> bool:
        return self._event.is_set()

    def get_result(self, timeout: Optional[float] = None) -> T:
        finished = self._event.wait(timeout)
        if not finished:
            raise TimeoutError("Timed out while waiting for result")

        if self._exception is not None:
            raise self._exception

        return self._result  # type: ignore # finished and no exception


"""Dictionary for passing arguments and synchronization from the server to
event handlers since only strings can be passed as additional arguments"""
_FUTURES: Dict[str, FusionFuture[Any]] = {}
_FUTURES_LOCK = Lock()  # lock for modifying futures dictionary


# stubs missing handler type
class DispatchHandler(adsk.core.CustomEventHandler, Generic[T]):  # type: ignore
    def __init__(self, handler: Callable[..., T]):
        super().__init__()
        self._handler = handler

    def notify(self, eventArgs: adsk.core.CustomEventArgs) -> None:
        # static method stub has useless self argument
        app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        ui = app.userInterface

        # Make sure a command isn't running before changes are made.
        if ui is not None and ui.activeCommand != "SelectCommand":
            # stubs are wrong
            ui.commandDefinitions.itemById("SelectCommand").execute()  # type: ignore

        future: FusionFuture[T] = _FUTURES[eventArgs.additionalInfo]

        try:
            result = self._handler(*future.args, **future.kwargs)
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)

        for handler in logger.handlers:
            handler.flush()


class EventInfo(Generic[T]):
    def __init__(self, id: str, handler: Callable[..., T]):
        self.id = id
        self.handler = handler


_FUSION_EVENTS: List[EventInfo[Any]] = []


def dispatcher(
    function: Callable[P, R], id: str
) -> Callable[  # type: ignore
    Concatenate[P, Optional[Callable[[Union[R, Exception]], None]]],  # type: ignore
    None,
]:
    @overload
    def wrapper(
        *args: P.args,  # type: ignore
        callback: Literal[None] = ...,  # type: ignore
        **kwargs: P.kwargs,  # type: ignore
    ) -> R:
        ...

    @overload
    def wrapper(
        *args: P.args,  # type: ignore
        callback: Callable[[Union[R, Exception]], None] = ...,  # type: ignore
        **kwargs: P.kwargs,  # type: ignore
    ) -> None:
        ...

    @wraps(function)
    def wrapper(
        *args: P.args,  # type: ignore
        callback: Optional[Callable[[Union[R, Exception]], None]] = None,  # type:ignore
        **kwargs: P.kwargs,  # type: ignore
    ) -> Optional[R]:
        # setup future for the dispatched method
        # unknown result type at this time
        future: FusionFuture[R] = FusionFuture(*args, callback=None, **kwargs)

        # add future to dict making sure it doesn't overwrite any existing ones
        with _FUTURES_LOCK:
            index = 0
            while True:
                key = f"{id}#{index}"
                if key in _FUTURES:
                    index += 1
                    continue

                _FUTURES[key] = future
                break

        # add a callback wrapper to delete the reference when the
        # dispatched function completes
        def handler(result_or_exception: Union[R, Exception]) -> None:
            if callback is not None:
                callback(result_or_exception)
            with _FUTURES_LOCK:
                _FUTURES.pop(key, None)

        future.callback = handler
        app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        logger.debug("Sending custom event %s", key)
        app.fireCustomEvent(id, key)

        # no callback provided, block until result is available to mimic the behaviour
        # of blocking service
        if callback is None:
            return future.get_result()

        return None

    # store some info in the wrapper
    setattr(wrapper, "unwrapped", property(lambda _: function))
    setattr(wrapper, "event_id", property(lambda _: id))

    return wrapper


EXPOSED_PREFIX = "exposed_"


class Fusion360ServiceMeta(type):
    def __new__(cls, name: str, bases: tuple[Any, ...], attrs: Dict[str, Any]):
        id_prefix = f"rpcad.{name}."

        def make_event(name: str, function: Callable[..., Any]) -> None:
            # since attribute names are unique in python they can be used
            # as unique event ids
            if name.startswith(EXPOSED_PREFIX):
                name = name[len(EXPOSED_PREFIX) :]  # noqa: E203

            id = f"{id_prefix}{name}"

            _FUSION_EVENTS.append(EventInfo(id, function))

            # replace the original method with dispatcher
            attrs[name] = dispatcher(function, id)

        # https://stackoverflow.com/a/3468410/13262469
        attr_name: str
        for attr_name, attr_value in attrs.items():
            # only wrap the exposed functions
            if isinstance(attr_value, types.FunctionType) and (
                attr_name.startswith("exposed_") or attr_name == "on_connect"
            ):
                make_event(attr_name, attr_value)

        return super().__new__(cls, name, bases, attrs)


def register_events() -> Dict[str, Tuple[adsk.core.CustomEvent, DispatchHandler[Any]]]:
    app: adsk.core.Application = adsk.core.Application.get()  # type: ignore

    events: Dict[str, Tuple[adsk.core.CustomEvent, DispatchHandler[Any]]] = {}
    for event_info in _FUSION_EVENTS:
        # setup fusion 360 event and attach a corresponding handler
        # using the original function
        event = app.registerCustomEvent(event_info.id)
        handler = DispatchHandler(event_info.handler)
        event.add(handler)

        # hold references to created events and handlers to avoid GC
        # reclaiming them
        events[event_info.id] = (event, handler)

    return events


def unregister_events(
    events: Iterable[
        Tuple[adsk.core.CustomEvent, adsk.core.CustomEventHandler]  # type:ignore
    ]
) -> None:
    app: adsk.core.Application = adsk.core.Application.get()  # type: ignore

    for event, handler in events:
        app.unregisterCustomEvent(event.eventId)
        event.remove(handler)


def ensure_valid_document(
    f: Callable[Concatenate["Fusion360Service", P], R]  # type: ignore
) -> Callable[Concatenate["Fusion360Service", P], R]:  # type: ignore
    @wraps(f)
    def wrapper(self: "Fusion360Service", *args: P.args, **kwargs: P.kwargs) -> R:
        self._validate_design()  # type: ignore # protected access
        return f(self, *args, **kwargs)

    return wrapper


_FUSION_ACCURACY = {
    Accuracy.Low: adsk.fusion.CalculationAccuracy.LowCalculationAccuracy,
    Accuracy.Medium: adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy,
    Accuracy.High: adsk.fusion.CalculationAccuracy.HighCalculationAccuracy,
    Accuracy.VeryHigh: adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy,
}

_FUSION_IMPORT_OPTIONS: Dict[
    str, Callable[[adsk.core.ImportManager, str], adsk.core.ImportOptions]
] = {
    ".step": adsk.core.ImportManager.createSTEPImportOptions,
    ".smt": adsk.core.ImportManager.createSMTImportOptions,
    ".sat": adsk.core.ImportManager.createSATImportOptions,
    ".iges": adsk.core.ImportManager.createIGESImportOptions,
    ".f3d": adsk.core.ImportManager.createFusionArchiveImportOptions,
}

_FUSION_EXPORT_OPTIONS: Dict[
    str,
    Callable[
        [adsk.fusion.ExportManager, str, adsk.fusion.Component],
        adsk.fusion.ExportOptions,
    ],
] = {
    ".step": adsk.fusion.ExportManager.createSTEPExportOptions,
    ".smt": adsk.fusion.ExportManager.createSMTExportOptions,
    ".sat": adsk.fusion.ExportManager.createSATExportOptions,
    ".iges": adsk.fusion.ExportManager.createIGESExportOptions,
    ".f3d": adsk.fusion.ExportManager.createFusionArchiveExportOptions,
}


def internal_to_si(value: float, unit: str, manager: adsk.core.UnitsManager) -> float:
    v = manager.convert(
        value,
        manager.internalUnits,
        unit,
    )

    if v == -1:
        app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        raise RuntimeError(f"Conversion failed:\n{app.getLastError()[0]}")

    return v


_FUSION_PHYSICAL_PROPERTY: Dict[
    PhysicalProperty,
    Callable[
        [
            Union[adsk.fusion.BRepBody, adsk.fusion.Component],
            adsk.fusion.PhysicalProperties,
            adsk.core.UnitsManager,
        ],
        Any,
    ],
] = {
    PhysicalProperty.Area: lambda _, props, manager: internal_to_si(
        props.area, "m^2", manager
    ),
    PhysicalProperty.Volume: lambda _, props, manager: internal_to_si(
        props.volume, "m^3", manager
    ),
    PhysicalProperty.Density: lambda _, props, manager: internal_to_si(
        props.density, "kg/m^3", manager
    ),
    PhysicalProperty.Mass: lambda _, props, manager: internal_to_si(
        props.mass, "kg", manager
    ),
    PhysicalProperty.CenterOfMass: lambda _, props, manager: [
        internal_to_si(f, "m", manager) for f in props.centerOfMass.getData()[1:]
    ],
    PhysicalProperty.BoundingBox: lambda body, _, manager: (
        [
            internal_to_si(f, "m", manager)
            for f in body.boundingBox.minPoint.getData()[1:]
        ],
        [
            internal_to_si(f, "m", manager)
            for f in body.boundingBox.maxPoint.getData()[1:]
        ],
    ),
}


def fusion_accuracy(accuracy: Accuracy) -> int:
    return _FUSION_ACCURACY.get(
        Accuracy(accuracy.value), adsk.fusion.CalculationAccuracy.LowCalculationAccuracy
    )


class Fusion360Service(CADService):
    def _setup(self) -> None:
        # setup fusion 360 objects
        self._app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        self._sync_design()

        ui = self._app.userInterface
        self._undo_command = ui.commandDefinitions.itemById("UndoCommand")

    def _sync_design(self) -> None:
        self._document: Optional[adsk.core.Document] = self._app.activeDocument
        self._design: Optional[adsk.fusion.Design] = adsk.fusion.Design.cast(
            self._app.activeProduct
        )

    def _validate_design(self) -> None:
        self._sync_design()

        if self._document is None:
            raise RuntimeError("No open documents")

        if self._design is None:
            raise RuntimeError("No open designs")

    def on_connect(self, conn: "Connection"):
        super().on_connect(conn)
        self._setup()

    def on_disconnect(self, conn: "Connection"):
        super().on_disconnect(conn)

        # no connections so doesn't matter that it's None, will be valid on
        # next connection
        self._app = None  # type: ignore
        self._design = None
        self._document = None

    @ensure_valid_document
    def _parameter(self, name: str) -> Parameter:
        params = self._design.allParameters  # type: ignore
        return cast_parameter(params.itemByName(name))

    @ensure_valid_document
    def _parameters(self) -> Dict[str, Parameter]:
        items: Dict[str, Parameter] = {}

        parameters = self._design.allParameters  # type: ignore
        for i in range(parameters.count):
            parameter = parameters.item(i)
            items[parameter.name] = cast_parameter(parameter)
        return items

    def _open_project(self, path: str) -> None:
        import_manager = self._app.importManager

        extension = os.path.splitext(path)[1]

        try:
            options = _FUSION_IMPORT_OPTIONS[extension](import_manager, path)
        except KeyError:
            raise ValueError(f"Invalid extension {extension}")

        self._document = import_manager.importToNewDocument(options)

        if self._document is None:
            raise RuntimeError(f"Could not open project '{path!s}'")

        self._document.activate()
        self._design = adsk.fusion.Design.cast(self._app.activeProduct)

    @ensure_valid_document
    def _save_project(self) -> None:
        self._document.save("Saved from an RPC service")  # type: ignore

    def _close_project(self) -> None:
        self._sync_design()
        if self._document is None:
            return

        self._document.close(False)
        self._document = None
        self._design = None

    @staticmethod
    def _select_mesh_body(
        component: adsk.fusion.Component, name: str
    ) -> Optional[adsk.fusion.MeshBody]:
        bodies = component.meshBodies
        for i in range(bodies.count):
            body = bodies.item(i)
            if body.name == name:
                return body

        return None

    @staticmethod
    def _select_brep_body(
        component: adsk.fusion.Component, name: str
    ) -> Optional[adsk.fusion.BRepBody]:
        return component.bRepBodies.itemByName(name)

    @ensure_valid_document
    def _select_component(self, name: str) -> Optional[adsk.fusion.Component]:
        return self._design.allComponents.itemByName(name)  # type: ignore

    @ensure_valid_document
    def _select_by_name(
        self, name: Optional[str]
    ) -> Optional[Union[adsk.fusion.Component, adsk.fusion.BRepBody]]:
        if name is None:
            return self._design.rootComponent  # type: ignore

        components = self._design.allComponents  # type: ignore
        component = components.itemByName(name)

        if component is not None:
            return component

        for i in range(components.count):
            body = self._select_brep_body(components.item(i), name)
            if body is not None:
                return body

        return None

    @ensure_valid_document
    def _export_project(self, path: str, *args: Any, **kwargs: Any) -> None:
        """
        Use kwargs to pass additional export values

        stl:
            body: str
                name of the body to export
            https://help.autodesk.com/view/fusion360/ENU/?guid=GUID-64f3e0ab-f3bc-445e-9505-7dba9d296ebd
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)

        # create a single exportManager instance
        export_manager = self._design.exportManager  # type: ignore

        extension = os.path.splitext(path)[1]

        geometry = self._design.rootComponent  # type: ignore
        body = geometry
        body_name = kwargs.pop("body", None)
        if extension == ".stl":
            if body_name is not None:
                body = self._select_by_name(body_name)

                if body is None:
                    raise ValueError(f"Body {body_name!r} not found")

            options = export_manager.createSTLExportOptions(body, path)
        else:
            if body_name is not None:
                # remaining export options all work on components only
                body = self._select_component(body_name)
                if body is None:
                    raise ValueError(f"No component {body_name!s} found")

            try:
                options = _FUSION_EXPORT_OPTIONS[extension](export_manager, path, body)
            except KeyError:
                raise ValueError(f"Invalid extension {extension}")

        for attr, value in kwargs.items():
            setattr(options, attr, value)

        export_manager.execute(options)

    @ensure_valid_document
    def _set_parameters(self, parameters: Dict[str, Union[str, float]]) -> None:
        for parameter, value_or_expression in parameters.items():
            param = self._design.allParameters.itemByName(parameter)  # type: ignore
            if param is None:
                raise ValueError(f"Invalid parameter name {parameter}")

            try:
                if isinstance(value_or_expression, str):
                    param.expression = str(value_or_expression)
                else:
                    param.value = float(value_or_expression)
            except TypeError:
                logger.exception(
                    "Failed setting '%s' to '%s'(%s)",
                    parameter,
                    value_or_expression,
                    type(value_or_expression),
                )
                raise

            logger.debug(
                "Set parameter %s = %s (%s)",
                parameter,
                param.expression,
                value_or_expression,
            )

    def _undo(self, count: int):
        if self._undo_command is None:
            raise RuntimeError("Could not get undo command")

        for _ in range(count):
            if not self._undo_command.execute():  # type: ignore # missing input
                break

    @ensure_valid_document
    def _reload(self):
        data_file = self._document.dataFile  # type: ignore
        self._document.close(False)  # type: ignore
        self._document = self._app.documents.open(data_file, True)
        self._design = adsk.fusion.Design.cast(self._app.activeProduct)

    def _debug(self):
        self.app = self._app
        self.document = self._document
        self.design = self._design
        self.undo_command = self._undo_command

    def _physical_properties(
        self, properties: Iterable[PhysicalProperty], part: str, accuracy: Accuracy
    ) -> Dict[PhysicalProperty, Any]:
        body = self._select_by_name(part)

        if body is None:
            raise ValueError(f"Could not find component or brep body {part}")

        physical_properties = body.getPhysicalProperties(
            fusion_accuracy(accuracy)  # type: ignore # stubs are wrong
        )
        values: Dict[PhysicalProperty, Any] = {}
        units = self._design.unitsManager  # type: ignore

        for prop in properties:
            prop = PhysicalProperty(prop.value)
            try:
                value = _FUSION_PHYSICAL_PROPERTY[prop](
                    body, physical_properties, units
                )
            except KeyError:
                raise ValueError(f"Invalid property {prop}")

            values[prop] = value

        return values


class Fusion360ServiceThreaded(Fusion360Service, metaclass=Fusion360ServiceMeta):
    pass


def cast_parameter(parameter: adsk.fusion.Parameter) -> Parameter:
    return Parameter(value=parameter.value, expression=parameter.expression)


class BasicFusionAddin:
    def __init__(self, log_dir: pathlib.Path = pathlib.Path(RPCAD_LOGDIR)):
        self.server: Optional[Server] = None
        self.logger = logging.getLogger("rpcad.Fusion360.AddIn")
        self.handler = handlers.RotatingFileHandler(
            f"{log_dir}/service.log",
            mode="a+",
            backupCount=5,
            delay=False,
            maxBytes=1024 * 1024,
        )

    def run(self, context: Any) -> None:
        ui = None
        try:
            app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
            ui = app.userInterface

            import rpcad

            rpcad = rpcad.reload()

            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            self.handler.setFormatter(formatter)

            root_logger = logging.getLogger(rpcad.__name__)
            root_logger.addHandler(self.handler)
            root_logger.setLevel(rpcad.RPCAD_LOGLEVEL)
            self.handler.setLevel(rpcad.RPCAD_LOGLEVEL)

            self.logger.info("Starting RPC server addin")
            self.start_service(context)

        except:  # noqa: E722
            if ui:
                ui.messageBox(  # type: ignore
                    "Failed:\n{}".format(traceback.format_exc())
                )
        finally:
            self.handler.flush()

            self._post_run(context)

    def stop(self, context: Any) -> None:
        ui = None
        try:
            app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
            ui = app.userInterface

            self.stop_service(context)

        except:  # noqa: E722
            if ui:
                ui.messageBox(  # type: ignore
                    "Failed:\n{}".format(traceback.format_exc())
                )
        finally:
            self.handler.flush()
            self.handler.close()
            logging.getLogger("rpcad").removeHandler(self.handler)

    def start_service(self, context: Any) -> None:
        from rpcad import RPCAD_LOGLEVEL

        try:
            self._create_service(context)

            if self.server is None:
                return
            self.server.logger.addHandler(self.handler)
            self.server.logger.setLevel(RPCAD_LOGLEVEL)
            self.server.logger.info(
                "Server created at %s:%s, starting",
                self.server.host,
                self.server.port,  # type: ignore
            )

            self._start_service(context)
        except Exception:
            self.logger.exception("RPC Server failed to start")
            app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
            ui = app.userInterface
            if ui:
                ui.messageBox(  # type: ignore
                    "Failed to start RPC server:\n{}".format(traceback.format_exc())
                )

    def stop_service(self, context: Any) -> None:
        if self.server is not None:
            self.server.close()
            self.logger.info("Server closed")
            self.server.logger.removeHandler(self.handler)

        self._stop_service(context)

    def _start_service(self, context: Any) -> None:
        if self.server is not None:
            self.server.start()

    @abstractmethod
    def _create_service(self, context: Any) -> None:
        ...

    @abstractmethod
    def _stop_service(self, context: Any) -> None:
        ...

    def _post_run(self, context: Any) -> None:
        pass
