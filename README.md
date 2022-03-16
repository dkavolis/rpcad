# rpcad

RPC client/server for design optimization using CAD

## Description

Basic RPC client and server for generating parametric CAD designs for
optimization without having to run it inside CAD environment. Works with local
CAD programs but should also work with remote ones.  

Currently only Fusion360 is supported. Call `Client.reload_project()` once in a
while to slow down memory leaks and increase time between crashes.

## Note

This project has been set up using PyScaffold 3.2.3. For details and usage
information on PyScaffold see [pyscaffold](https://pyscaffold.org/).
