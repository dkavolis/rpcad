# -*- coding: utf-8 -*-
from pkg_resources import get_distribution, DistributionNotFound

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = __name__
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = "unknown"
finally:
    del get_distribution, DistributionNotFound


def ensure_rpyc():
    try:
        import rpyc
    except (ImportError, ModuleNotFoundError):
        import subprocess
        import sys

        subprocess.run(
            [sys.executable, "-m", "pip", "install", "rpyc", "--user"], check=True
        )
        import rpyc  # noqa: F401


ensure_rpyc()
del ensure_rpyc


def reload_service_modules(*args):
    from rpcad import common, parameter, service, commands
    import importlib

    importlib.reload(common)
    importlib.reload(parameter)
    importlib.reload(commands)
    importlib.reload(service)
    for module in args:
        importlib.reload(module)


# above is setup needed for submodules
from rpcad.client import Client  # noqa: E402
from rpcad.parameter import Parameter  # noqa: E402
from rpcad.common import (  # noqa: E402
    RPCAD_HOSTNAME,
    RPCAD_PORT,
    RPCAD_FALLBACK_PORT,
    RPCAD_LOGDIR,
    RPCAD_LOGLEVEL,
)
from rpcad.commands import Command, PhysicalProperty, Accuracy  # noqa: E402

__all__ = [
    "Accuracy",
    "Client",
    "Command",
    "Parameter",
    "PhysicalProperty",
    "reload_service_modules",
    "RPCAD_FALLBACK_PORT",
    "RPCAD_HOSTNAME",
    "RPCAD_LOGDIR",
    "RPCAD_LOGLEVEL",
    "RPCAD_PORT",
]
