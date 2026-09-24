# nctools

Tools for a NETCONF client to interact with a NETCONF server, such as
listing and downloading all the YANG modules a device supports.

## Installation

```
pip install netconf-yang-tools
```

Or, from a checkout of this repository:

```
pip install .
```

## Usage

```
nctools --host <device> -u <username> -p <password> --list
nctools --host <device> -u <username> -p <password> --download
```

`--list` queries the device for its supported YANG modules and marks them
for download in `/tmp/yang/<host>` (each device gets its own subdirectory,
so concurrent runs against different devices don't collide; override with
`-d`/`--dir`). `--download` fetches and writes to disk every module marked
by a previous `--list` run. Pass `--debug` to either command for verbose
NETCONF/transport-level logging.
