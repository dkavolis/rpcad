#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from __future__ import annotations

from pkg_resources import get_distribution, DistributionNotFound
import types

try:
    # Change here if project is renamed and does not equal the package name
    dist_name = __name__
    __version__ = get_distribution(dist_name).version
except DistributionNotFound:
    __version__ = "unknown"
finally:
    del get_distribution, DistributionNotFound


def ensure_rpyc() -> None:
    # pyright: reportUnusedImport=false
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


def reload() -> types.ModuleType:
    """
    reload reload rpcad module without restarting Python

    Returns
    -------
    types.ModuleType
        reloaded rpcad module
    """
    import importlib
    import rpcad

    rpcad = importlib.reload(rpcad)

    from rpcad import common, parameter, commands, service

    importlib.reload(common)
    importlib.reload(parameter)
    importlib.reload(commands)
    importlib.reload(service)

    try:
        from rpcad import fusion

        fusion = importlib.reload(fusion)
    except ImportError:
        pass

    return rpcad


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
from rpcad.async_client import AsyncResult, AsyncClient  # noqa: E402
from rpcad.commands import Command, PhysicalProperty, Accuracy  # noqa: E402

__all__ = [
    "Accuracy",
    "AsyncClient",
    "AsyncResult",
    "Client",
    "Command",
    "Parameter",
    "PhysicalProperty",
    "reload",
    "RPCAD_FALLBACK_PORT",
    "RPCAD_HOSTNAME",
    "RPCAD_LOGDIR",
    "RPCAD_LOGLEVEL",
    "RPCAD_PORT",
]
