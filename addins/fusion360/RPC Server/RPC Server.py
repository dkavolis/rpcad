# Author-D. Kavolis
# Description-RPC server for modifying designs.

import os
import sys
import traceback
from threading import Thread
from typing import Optional

import adsk.cam
import adsk.core
import adsk.fusion
import adsk

sys.path.append(os.path.dirname(__file__))


SERVER = None
PROCESS: Optional[Thread] = None
EVENTS = None


def start_service():
    from rpcad import reload_service_modules, fusion

    # make sure any changes are picked up by fusion 360 on restart since the
    # embedded python interpreter does not unload modules by default
    reload_service_modules(fusion)

    from rpcad.fusion import Fusion360Service
    from rpyc.utils.server import ThreadPoolServer

    global SERVER

    # use requestBatchSize = 1 since most CAD functions can take a while to
    # complete, especially when they have to use events to communicate and wait
    # for the main thread to finish
    SERVER = Fusion360Service.create_server(server=ThreadPoolServer, requestBatchSize=1)
    SERVER.start()


def run(context):
    ui = None
    try:
        app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        ui = app.userInterface

        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        import rpcad
        import importlib

        importlib.reload(rpcad)

        from rpcad.fusion import register_events

        global EVENTS
        EVENTS = register_events()

        PROCESS = Thread(target=start_service, daemon=True)
        PROCESS.start()

        # need to hold references to events and handlers so that they don't go
        # out of scope
        adsk.autoTerminate(False)

    except:  # noqa: E722
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))  # type: ignore


def stop(context):
    ui = None
    try:
        app: adsk.core.Application = adsk.core.Application.get()  # type: ignore
        ui = app.userInterface

        if SERVER is not None:
            SERVER.close()

        if PROCESS is not None:
            PROCESS.join()

        if EVENTS is not None:
            from rpcad.fusion import unregister_events

            unregister_events(EVENTS.values())

    except:  # noqa: E722
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))  # type: ignore
