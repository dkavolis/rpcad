# -*- coding: utf-8 -*-
"""
    Setup file for rpcad.
    Use setup.cfg to configure your project.

    This file was generated with PyScaffold 3.2.3.
    PyScaffold helps you to put up the scaffold of your new Python project.
    Learn more under: https://pyscaffold.org/
"""


import glob
import platform
import sys
import os
from subprocess import check_call
import shutil

from pkg_resources import VersionConflict, require
from setuptools import setup
from setuptools.command.install import install


class PostInstallCommand(install):
    """Post-installation for installation mode."""

    def run(self):
        install.run(self)

        pl = platform.system()
        if pl == "Windows":
            self.install_win()
        elif pl == "Darwin":
            self.install_mac()

    def install_win(self):
        self.install_fusion360(
            os.path.expandvars("%LocalAppData%/Autodesk/webdeploy/production"),
            os.path.expandvars("%AppData%/Autodesk/Autodesk Fusion 360/API/AddIns"),
        )

    def install_mac(self):
        pass

    def install_fusion360(self, fusion360_dir: str, addin_dir: str) -> None:
        source_dir = os.path.abspath(os.path.dirname(__file__))
        requirements = os.path.join(source_dir, "requirements.txt")
        print("-- Looking for python executables in ", fusion360_dir)
        for python_dir in glob.glob(f"{fusion360_dir}/**/Python"):
            print("-- Installing rpyc for ", python_dir)
            check_call(
                ["python", "-m", "pip", "install", "-r", requirements, "--user"],
                cwd=python_dir,
            )

        dst = os.path.join(addin_dir, "RPC Server")
        if os.path.exists(dst):
            shutil.rmtree(dst)

        print("-- Copying addin to ", addin_dir)
        addin = shutil.copytree(
            os.path.join(source_dir, "addins", "fusion360", "RPC Server"),
            os.path.join(addin_dir, "RPC Server"),
        )
        shutil.copytree(
            os.path.join(source_dir, "src", "rpcad"), os.path.join(addin, "rpcad")
        )


try:
    require("setuptools>=38.3")
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    sys.exit(1)


if __name__ == "__main__":
    setup(use_pyscaffold=True, cmdclass={"install": PostInstallCommand})
