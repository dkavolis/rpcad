# rpcad

RPC client/server for design optimization using CAD

## Description

Basic RPC client and server for generating parametric CAD designs for
optimization without having to run it inside CAD environment. Works with local
CAD programs but should also work with remote ones.

Supported environment variables:
| Variable              | Default       | Description                                       |
| --------------------- | ------------- | ------------------------------------------------- |
| `RPCAD_HOSTNAME`      | `"localhost"` | Default client host name parameter value          |
| `RPCAD_PORT`          | `18888`       | Default client port parameter value               |
| `RPCAD_FALLBACK_PORT` | `18898`       | Fallback client port if default failed to connect |
| `RPCAD_LOGDIR`        | `..`          | Default service log dir, defaults to addin dir    |
| `RPCAD_LOGLEVEL`      | `"DEBUG"`     | Default service log level, see `logging`          |

Currently only Fusion360 is supported. Call `Client.reload_project()` once in a
while to slow down memory leaks and increase time between crashes. Oneshot
server will block until the connection is closed and seems more stable than the
threaded server. Supports setting and querying parameters, querying physical
properties, saving and reloading focused projects, exporting bodies to
supported formats and undoing commands.

With the addin running in CAD, a basic example with Fusion360:

```python
>>> import rpcad
>>> c = rpcad.Client()
>>> p = c.parameter("length")
>>> p
<rpcad.parameter.Parameter object at 0x000001EFBDF773C8>
>>> p.value
80.0
>>> p.expression
'800.00 mm'
>>> c.set_parameters(length=90)
>>> str(c.parameter("length"))
'90.0 (900.00 mm)'
```

For best results in population based optimizations, submit a batch of
parameters at the start of every generation asynchronously through
`AsyncClient` (untested) or by running `Client` in a separate process.  

## Note

This project has been set up using PyScaffold 3.2.3. For details and usage
information on PyScaffold see [pyscaffold](https://pyscaffold.org/).
