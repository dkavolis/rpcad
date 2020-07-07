# Author-D. Kavolis
# Description-RPC server for modifying designs.

import adsk.core
import adsk.fusion
import adsk.cam
import traceback
from threading import Thread
import sys
import os


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
