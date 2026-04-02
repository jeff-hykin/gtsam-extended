# GTSAM macOS Wheel Builder — Agent Context

## What This Repo Does

Builds self-contained Python wheels for [GTSAM](https://gtsam.org/) (Georgia Tech Smoothing And Mapping) on macOS, specifically targeting **Apple Silicon (arm64)**. No pre-built arm64 macOS wheels exist on PyPI, so this repo builds from source using Nix for reproducibility and dependency management.

The output is a `.whl` file with all non-system dylibs bundled inside it (via `@loader_path/.dylibs/`), so `pip install gtsam-*.whl` just works in any Python 3.12 venv without needing Homebrew, Nix, or any other system dependencies at runtime.

## Why This Exists

The upstream consumer is `~/repos/dimos` — a robotics project that uses GTSAM for pose graph optimization (iSAM2) in `dimos/navigation/smartnav/modules/pgo/pgo.py`. That project's `pyproject.toml` has platform guards for GTSAM but no macOS arm64 wheel was available.

## Build Commands

```bash
# Build the Python wheel (default target)
nix build

# Build just the C++ library
nix build .#gtsam-cpp

# Enter a dev shell with all build deps available
nix develop
```

The wheel lands in `./result/gtsam-4.3a1-cp312-cp312-macosx_14_0_arm64.whl`.

## Architecture

### `flake.nix`

Two packages:

1. **`gtsam-cpp`** — Builds the GTSAM C++ library only (`-DGTSAM_BUILD_PYTHON=OFF`). Installed to a Nix store path. Also used by `gtsam-python-wheel` as a reference for resolving `@rpath` library paths during dylib bundling.

2. **`gtsam-python-wheel`** (default) — Builds GTSAM + Python bindings from source, produces a `.whl` via `setup.py bdist_wheel`, then:
   - Unpacks the wheel with `zipfile`
   - Runs `bundle_dylibs.py` to make it self-contained
   - Repacks as a `.whl`
   - `dontFixup = true` prevents Nix from running its own patchelf/install_name_tool passes

Both packages share `commonCmakeFlags` and `commonBuildInputs`.

### `bundle_dylibs.py`

Custom Mach-O dylib bundler (replaces `delocate` which doesn't work in the Nix sandbox because Nix's `otool` lacks the `-m` flag). It:

1. Scans each `.so` file with `otool -L`
2. For `/nix/store/*` deps: copies the dylib into `.dylibs/`, rewrites the load command to `@loader_path/.dylibs/<name>`
3. For `@rpath/*` deps: resolves via `gtsam-cpp`'s lib dir, bundles, rewrites
4. For `/usr/lib/*` and `/System/*` deps: leaves them alone (system libs)
5. Recursively processes deps of bundled dylibs (so boost's deps get bundled too)
6. Sets each bundled dylib's ID to `@loader_path/<name>` (relative to `.dylibs/`)
7. Strips all `LC_RPATH` entries (they point to Nix sandbox build dirs)
8. Ad-hoc codesigns everything (if `codesign` is available)

**Key insight that took several iterations to discover**: Using shell-based `install_name_tool` loops with `libc++` paths caused silent corruption — the `+` characters in `libc++.1.dylib` interacted badly with shell processing, creating phantom duplicate entries. The Python script avoids this entirely by using `subprocess.run` with list args (no shell expansion).

### Bundled Dylibs in the Wheel

The final wheel contains these in `gtsam/.dylibs/`:
- `libgtsam.4.dylib` — the core GTSAM library
- `libmetis-gtsam.dylib` — graph partitioning (bundled with GTSAM source)
- `libcephes-gtsam.1.dylib` — special math functions (bundled with GTSAM source)
- `libboost_graph.dylib`, `libboost_serialization.dylib`, `libboost_timer.dylib`, `libboost_chrono.dylib`
- `libtbb.12.dylib`, `libtbbmalloc.2.dylib` — Intel TBB for parallelism

System libs left as-is: `/usr/lib/libSystem.B.dylib`, `/usr/lib/libc++.1.dylib`

## Source Version

Currently pinned to GTSAM `develop` branch (`sha256-Uf71hmnRN5sXK5gWgCGkKUQlLWQALWH332wEmMsmHZI=`).

- **GTSAM 4.2 tag doesn't work** with modern Boost (1.90+) — Boost removed the `system` component as a separate library. The `develop` branch has the fix.
- The `develop` branch tracks what the `gtsam-develop` PyPI package provides, so the API is compatible with `gtsam>=4.2`.

## CMake Flags Rationale

| Flag | Why |
|------|-----|
| `GTSAM_USE_SYSTEM_EIGEN=ON` | Avoids bundling a private Eigen; matches Docker builds in dimos |
| `GTSAM_BUILD_WITH_MARCH_NATIVE=OFF` | Avoids x86-specific instructions; arm64 gets NEON by default |
| `GTSAM_BUILD_TESTS=OFF` | Saves significant build time |
| `GTSAM_BUILD_UNSTABLE=OFF` | Not needed; experimental modules |
| `GTSAM_WITH_TBB=ON` | Enables multi-threaded optimization |
| `Python_ROOT_DIR=${python}` | Ensures CMake finds Nix's Python 3.12, not system Python |
| `Python_FIND_STRATEGY=LOCATION` | Tells CMake to prefer `Python_ROOT_DIR` over system search |

## Known Issues & Pitfalls

1. **`delocate` doesn't work in Nix sandbox** — Nix's `otool` doesn't support the `-m` flag that `delocate` requires. That's why we have `bundle_dylibs.py`.

2. **Shell-based install_name_tool + libc++ = corruption** — Earlier attempts using bash loops with `install_name_tool -change` produced phantom duplicate Mach-O load commands when processing paths containing `+` (like `libc++.1.dylib`). The Python script avoids this.

3. **`pyparsing` must be available to the build Python** — GTSAM's wrapper generator (`gtwrap`) imports `pyparsing` at build time. It's included in `nativeBuildInputs` via `pythonPackages.pyparsing`.

4. **`codesign` not available in Nix sandbox** — The script handles this gracefully. The unsigned binaries work fine for local development; only App Store / notarization requires proper signing.

5. **Source hash will change** — The `develop` branch moves. When updating, use `nix build` and let the hash mismatch error give you the new hash.

6. **Python version is hardcoded to 3.12** — Change `python = pkgs.python312;` in `flake.nix` to target a different version. The wheel filename encodes the Python version (`cp312`).

## Testing the Wheel

```bash
# Create a clean venv and test
python3.12 -m venv /tmp/test_gtsam
/tmp/test_gtsam/bin/pip install numpy ./result/gtsam-*.whl
/tmp/test_gtsam/bin/python -c "
import gtsam, numpy as np
isam = gtsam.ISAM2(gtsam.ISAM2Params())
pose = gtsam.Pose3(gtsam.Rot3(np.eye(3)), gtsam.Point3(0,0,0))
g = gtsam.NonlinearFactorGraph()
v = gtsam.Values()
v.insert(0, pose)
g.add(gtsam.PriorFactorPose3(0, pose, gtsam.noiseModel.Diagonal.Variances(np.full(6, 1e-12))))
isam.update(g, v)
print(isam.calculateBestEstimate().atPose3(0).translation())
"
```

## Likely Changes You Might Want to Make

- **Pin to a stable tag**: Change `rev = "develop"` to a specific commit or tag, update `sha256`
- **Support multiple Python versions**: Parameterize `python = pkgs.python3XX;` and build multiple wheels
- **Add x86_64 support**: Already handled by `eachDefaultSystem` — just build on an Intel Mac or use `--system x86_64-darwin`
- **Publish to a private PyPI**: Add a `publish` script or CI step that uploads `result/*.whl`
- **Update GTSAM version**: Change `rev`, clear `sha256` to `lib.fakeHash`, build to get new hash
