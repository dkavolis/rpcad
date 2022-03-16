# Author-D. Kavolis
# Description-RPC server for modifying designs.

from threading import Thread
from typing import Any, Optional, Tuple, Dict
import time
import sys
import os

import adsk.cam
import adsk.core
import adsk

# the addin directory is not in search path by default
sys.path.append(os.path.dirname(__file__))
from rpcad.fusion import BasicFusionAddin, DispatchHandler  # noqa: E402


class FusionServer(BasicFusionAddin):
    def __init__(self):
        super().__init__()
        self.process: Optional[Thread] = None
        self.events: Optional[
            Dict[str, Tuple[adsk.core.CustomEvent, DispatchHandler[Any]]]
        ] = None

    def _create_service(self, context: Any) -> None:
        from rpcad.fusion import Fusion360ServiceThreaded
        from rpyc.utils.server import ThreadPoolServer

        # use requestBatchSize = 1 since most CAD functions can take a while to
        # complete, especially when they have to use events to communicate and wait
        # for the main thread to finish
        self.server = Fusion360ServiceThreaded.create_server(
            server=ThreadPoolServer, requestBatchSize=1
        )

    def _start_service(self, context: Any) -> None:
        from rpcad.fusion import register_events

        self.events = register_events()
        self.logger.info("Registered custom events")

        self.process = Thread(
            target=super()._start_service, daemon=False, args=(context,)
        )
        self.process.start()

        time.sleep(0.05)

        # need to hold references to events and handlers so that they don't go
        # out of scope unless server failed to start
        if self.process.is_alive():
            adsk.autoTerminate(False)
        else:
            self.logger.error("Failed to start service")
            adsk.terminate()

    def _stop_service(self, context: Any) -> None:
        if self.process is not None:
            self.process.join()

        if self.events is not None:
            from rpcad.fusion import unregister_events

            unregister_events(self.events.values())
            self.logger.info("Events unregistered")


SERVER = FusionServer()


def run(context: Any):
    SERVER.run(context)


def stop(context: Any):
    SERVER.stop(context)
