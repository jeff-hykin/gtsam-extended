# gtsam-extended

Pre-built GTSAM wheels for all platforms, published under a single package name so installation is the same everywhere.

There is no source code in this repo. It downloads official wheels from PyPI (`gtsam-develop`) and builds additional wheels with Nix for platforms/versions that are missing (e.g. Python 3.10 on macOS arm64). All wheels are renamed to `gtsam-extended` and uploaded to PyPI with a unified version.

## Install

```sh
pip install gtsam-extended
```

Works as a drop-in replacement — just `import gtsam` as usual.

## Platform Coverage

| | macOS (arm64 + x86_64) | Linux x86_64 | Linux aarch64 (Jetson) |
|---|---|---|---|
| Python 3.10 | yes (nix-built) | - | - |
| Python 3.11 | yes | yes | yes |
| Python 3.12 | yes | yes | yes |
| Python 3.13 | yes | yes | yes |
| Python 3.14 | yes | yes | yes |

## Building & Publishing

See [PUBLISHING.md](PUBLISHING.md) for details.

---

# README - Georgia Tech Smoothing and Mapping Library

**Important Note**

As of Dec 2021, the `develop` branch is officially in "Pre 4.2" mode. A great new feature we will be adding in 4.2 is *hybrid inference* a la DCSLAM (Kevin Doherty et al) and we envision several API-breaking changes will happen in the discrete folder.

In addition, features deprecated in 4.1 will be removed. Please use the last [4.1.1 release](https://github.com/borglab/gtsam/releases/tag/4.1.1) if you need those features. However, most (not all, unfortunately) are easily converted and can be tracked down (in 4.1.1) by disabling the cmake flag `GTSAM_ALLOW_DEPRECATED_SINCE_V42`.

## What is GTSAM?

GTSAM is a C++ library that implements smoothing and mapping (SAM) in robotics and vision, using Factor Graphs and Bayes Networks as the underlying computing paradigm rather than sparse matrices.

The current support matrix is:

| Platform     | Compiler  | Build Status  |
|:------------:|:---------:|:-------------:|
| Ubuntu 18.04 | gcc/clang | ![Linux CI](https://github.com/borglab/gtsam/workflows/Linux%20CI/badge.svg) |
| macOS        | clang     | ![macOS CI](https://github.com/borglab/gtsam/workflows/macOS%20CI/badge.svg) |
| Windows      | MSVC      | ![Windows CI](https://github.com/borglab/gtsam/workflows/Windows%20CI/badge.svg) |

On top of the C++ library, GTSAM includes wrappers for MATLAB & Python.

## Quickstart

```sh
mkdir build
cd build
cmake ..
make check (optional, runs unit tests)
make install
```

Prerequisites: Boost >= 1.65, CMake >= 3.0, a modern compiler (at least gcc 4.7.3 on Linux). Optional: Intel TBB, Intel MKL.

## Wrappers

Support for MATLAB and Python wrappers is provided.

## Citation

The recommended citation uses the BibTeX entry for `borglab/gtsam` (Frank Dellaert and GTSAM Contributors, version 4.2a8, 2022). Additional citations are provided for the "Factor Graphs for Robot Perception" book and the IMU preintegration scheme.

## The Preintegrated IMU Factor

Includes a state-of-the-art IMU handling scheme based on work by Lupton/Sukkarieh (2012) and Forster/Carlone/Dellaert/Scaramuzza (2015), with an efficient implementation integrating on the NavState tangent space.

## Additional Information

- [GTSAM users Google group](https://groups.google.com/forum/#!forum/gtsam-users)
- Open source under the BSD license
- Developed in the lab of Frank Dellaert at Georgia Institute of Technology
