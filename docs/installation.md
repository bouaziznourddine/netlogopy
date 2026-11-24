# Installation

## Requirements

- Python 3.8 or newer.
- [NetLogo](https://ccl.northwestern.edu/netlogo/download.shtml) 6.x or 7.x.
- Java: NetLogo 6.3 and newer include a suitable Java runtime. NetLogo 6.2 and
  older include Java 8, which is too old for JPype: install Java 11 or newer
  (for example `conda install -c conda-forge openjdk=17`) or set `JAVA_HOME`.
- [JPype1](https://pypi.org/project/JPype1/), installed automatically.

## With pip

```bash
pip install netlogopy
```

With pandas and numpy (DataFrames and array grids):

```bash
pip install "netlogopy[data]"
```

## With conda

The repository has an `environment.yml` with Python, Java 17 and netlogopy:

```bash
conda env create -f environment.yml
```

```bash
conda activate netlogopy-env
```

## Where netlogopy looks for NetLogo and Java

NetLogo
:   the `netlogo_home` argument, else the `NETLOGO_HOME` environment variable,
    else the newest NetLogo installed in the usual places
    (`C:/Program Files/NetLogo *`, `/Applications/NetLogo *`, `~/NetLogo *`,
    `/opt/NetLogo *`).

Java
:   the `java_home` argument, NetLogo's own runtime, `JAVA_HOME`, the active
    conda environment, then the runtimes of other NetLogo installations.

## Check the installation

```bash
python -m netlogopy
```

It prints the JPype, NetLogo and Java it finds, and starts NetLogo headless
once.

## Platforms

| | Headless sessions | NetLogo window |
|---|---|---|
| Windows | yes (tested) | yes (tested) |
| Linux | yes | yes, with a display |
| macOS | yes | no: AWT must own the main thread |

`NETLOGOPY_HEADLESS=1` turns every window off, to run window scripts in tests,
in CI or on a server.
