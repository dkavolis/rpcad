# Author-D. Kavolis
# Description-RPC server for modifying designs.

import os
import sys
import traceback

# from threading import Thread

import adsk.cam
import adsk.core
import adsk.fusion

sys.path.append(os.path.dirname(__file__))


SERVER = None
PROCESS = None

# Fusion360 doesn't like it's API called from worker threads so have to use plugin with
# a server in main thread, have to relaunch server for new connections
# Threaded server works ok at low API call rates but completely breaks down when many
# commands are executed sequentially


def start_service():
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from rpcad.fusion import Fusion360Service
    from rpyc.utils.server import OneShotServer

    global SERVER
    SERVER = Fusion360Service.create_server(server=OneShotServer)
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

        # PROCESS = Thread(target=start_service, daemon=True)
        # PROCESS.start()
        start_service()

    except:  # noqa: E722
        if ui:
            ui.messageBox("Failed:\n{}".format(traceback.format_exc()))


# not used in scripts but left for possible addin functionality
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
