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

import os


def ensure_rpyc():
    try:
        import rpyc
    except ImportError:
        import subprocess
        import sys

        subprocess.call([sys.executable, "-m", "pip", "install", "rpyc", "--user"])
        import rpyc  # noqa: F401


ensure_rpyc()
del ensure_rpyc


RPCAD_HOSTNAME = os.environ.get("RPCAD_HOSTNAME", "localhost")
RPCAD_PORT = os.environ.get("RPCAD_PORT", 18_888)
RPCAD_FALLBACK_PORT = os.environ.get("RPCAD_FALLBACK_PORT", 18_898)

del os
