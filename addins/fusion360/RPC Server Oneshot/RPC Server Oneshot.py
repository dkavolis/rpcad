# Author-D. Kavolis
# Description-RPC server for modifying designs.

import os
import sys
import traceback
import logging
from logging import handlers

import adsk.cam
import adsk.core
import adsk.fusion
import adsk

addin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(addin_dir)


SERVER = None


logger = logging.getLogger("rpcad.Fusion360.AddIn")
handler = handlers.RotatingFileHandler(
    f"{addin_dir}/service.log",
    mode="a+",
    backupCount=5,
    delay=False,
    maxBytes=1024 * 1024,
)


def start_service():
    from rpcad import RPCAD_LOGLEVEL
    from rpcad.fusion import Fusion360Service
    from rpyc.utils.server import OneShotServer

    global SERVER

    try:
        SERVER = Fusion360Service.create_server(server=OneShotServer)
        SERVER.logger.addHandler(handler)
        SERVER.logger.setLevel(RPCAD_LOGLEVEL)
        logger.info("Server created at %s:%s, starting", SERVER.host, SERVER.port)
        SERVER.start()
    except Exception:
        logger.exception("RPC Server failed")
        app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        ui = app.userInterface
        if ui:
            ui.messageBox("Failed to start RPC server:\n{}".format(traceback.format_exc()))  # type: ignore


def run(context):
    ui = None
    try:
        app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        ui = app.userInterface

        import rpcad

        rpcad = rpcad.reload()

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        root_logger = logging.getLogger(rpcad.__name__)
        root_logger.addHandler(handler)
        root_logger.setLevel(rpcad.RPCAD_LOGLEVEL)
        handler.setLevel(rpcad.RPCAD_LOGLEVEL)

        logger.info("Starting RPC server addin")
        start_service()

    except:  # noqa: E722
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))  # type: ignore
    finally:
        handler.flush()


def stop(context):
    ui = None
    try:
        app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        ui = app.userInterface

        if SERVER is not None:
            SERVER.close()
            logger.info("Server closed")
            SERVER.logger.removeHandler(handler)

    except:  # noqa: E722
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))  # type: ignore
    finally:
        handler.flush()
        handler.close()
        logging.getLogger("rpcad").removeHandler(handler)
