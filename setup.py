#!/usr/bin/env python3
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
from pathlib import Path
from typing import Optional

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
        elif pl == "Linux":
            self.install_linux()
        elif pl == "Darwin":
            self.install_mac()

    def install_win(self):
        self.install_fusion360(
            Path(os.path.expandvars("%LocalAppData%/Autodesk/webdeploy/production")),
            Path(
                os.path.expandvars("%AppData%/Autodesk/Autodesk Fusion 360/API/AddIns")
            ),
        )

    def install_mac(self):
        print(
            "Fusion360 Mac paths are not implemented, addin not installed. "
            "Install manually by copying addins in 'addins/fusion360' to Fusion360 "
            "addins directory and copying 'src/rpcad' into each.",
            file=sys.stderr,
        )

    def install_linux(self):
        # potentially FreeCAD
        pass

    def install_fusion360(self, fusion360_dir: Path, addin_dir: Path) -> None:
        import rpyc

        rpyc_version = rpyc.version.version_string  # type: ignore

        print("-- Looking for python executables in ", fusion360_dir)
        pydir: Optional[Path] = None
        for python_exe in glob.glob(f"{fusion360_dir}/**/Python/[Pp]ython*"):
            executable = Path(python_exe)
            python_dir = executable.parent
            if executable.suffix in (".dll", ".so", ".dylib"):
                # not an executable
                continue

            print(f"-- Installing rpyc=={rpyc_version} for {python_dir}")
            check_call(
                [
                    executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    f"rpyc=={rpyc_version}",
                    "--user",
                ],
                cwd=python_dir,
            )
            pydir = python_dir

        self.install_fusion360_addin("RPC Server", pydir, addin_dir)
        self.install_fusion360_addin("RPC Server Oneshot", pydir, addin_dir)

    def install_fusion360_addin(
        self, name: str, python_dir: Optional[Path], addin_dir: Path
    ) -> None:
        source_dir = Path(__file__).absolute().parent
        main_dir = source_dir / "addins" / "fusion360"
        dst = addin_dir / name
        if os.path.exists(dst):
            shutil.rmtree(dst)

        print(f"-- Copying addin to '{addin_dir}'")
        addin = shutil.copytree(main_dir / name, dst)
        shutil.copytree(source_dir / "src" / "rpcad", addin / "rpcad")

        if python_dir is None:
            return

        pypath = python_dir.parent / "Api" / "Python" / "packages"
        with open(addin / ".env", "w") as file:
            file.write(f"PYTHONPATH={pypath}".replace("\\", "/"))


try:
    require("setuptools>=38.3")
except VersionConflict:
    print("Error: version of setuptools is too old (<38.3)!")
    sys.exit(1)


if __name__ == "__main__":
    setup(use_pyscaffold=True, cmdclass={"install": PostInstallCommand})  # type: ignore
