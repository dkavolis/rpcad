# Author-D. Kavolis
# Description-RPC server for modifying designs.

import pathlib
from typing import Any
import sys
import os

import adsk

# the addin directory is not in search path by default
sys.path.append(os.path.dirname(__file__))
from rpcad.fusion import BasicFusionAddin  # noqa: E402


class FusionServer(BasicFusionAddin):
    def __init__(self):
        super().__init__(pathlib.Path(__file__).parent)

    def _create_service(self, context: Any) -> None:
        from rpcad.fusion import Fusion360Service
        from rpyc.utils.server import OneShotServer

        self.server = Fusion360Service.create_server(server=OneShotServer)

    def _post_run(self, context: Any) -> None:
        # oneshot so there's no reason to keep this script continuing
        adsk.terminate()


SERVER = FusionServer()


def run(context: Any):
    SERVER.run(context)


def stop(context: Any):
    SERVER.stop(context)
