#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import os

RPCAD_HOSTNAME = os.environ.get("RPCAD_HOSTNAME", "localhost")
RPCAD_PORT = os.environ.get("RPCAD_PORT", 18_888)
RPCAD_FALLBACK_PORT = os.environ.get("RPCAD_FALLBACK_PORT", 18_898)
RPCAD_LOGDIR = os.environ.get(
    "RPCAD_LOGDIR", os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
RPCAD_LOGLEVEL = os.environ.get("RPCAD_LOGLEVEL", "DEBUG")

del os
