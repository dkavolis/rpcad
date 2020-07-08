# Author-D. Kavolis
# Description-RPC server for modifying designs.

import os
import sys
import traceback
from threading import Thread

import adsk.cam
import adsk.core
import adsk.fusion

sys.path.append(os.path.dirname(__file__))


SERVER = None
PROCESS = None


def start_service():
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from rpcad.fusion import Fusion360Service

    global SERVER
    SERVER = Fusion360Service.create_server()
    SERVER.start()


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        import rpcad
        import importlib

        importlib.reload(rpcad)
        from rpcad import reload_service_modules, fusion

        # make sure any changes are pickup by fusion 360 on restart
        reload_service_modules(fusion)

        PROCESS = Thread(target=start_service, daemon=True)
        PROCESS.start()

    except:  # noqa: E722
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


def stop(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        if SERVER is not None:
            SERVER.close()

        if PROCESS is not None:
            PROCESS.join()

    except:  # noqa: E722
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))
