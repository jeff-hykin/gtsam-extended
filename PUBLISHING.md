# Publishing to PyPI

This package uploads GTSAM wheels to PyPI under the distribution name `gtsam-extended`.

## What Gets Uploaded

Wheels from two sources, all renamed to `gtsam_extended` with a normalized version:

**From PyPI (`gtsam-develop`):**
- cp311/cp312/cp313/cp314 x macOS universal2
- cp311/cp312/cp313/cp314 x Linux x86_64 (manylinux2014)
- cp311/cp312/cp313/cp314 x Linux aarch64 (manylinux2014 — works on Jetson/Ubuntu 20.04+)

**From local Nix build (`result/`):**
- cp310 x macOS arm64 (and any other custom builds)

Each wheel:
- Contains the `gtsam` package (so `import gtsam` works)
- Has distribution name `gtsam-extended` (avoids conflict with official `gtsam` package)
- Version normalized to match `pyproject.toml` so PyPI accepts the batch

## Quick Publish

```bash
./run/publish
```

This will:
1. Download latest `gtsam-develop` wheels from PyPI
2. Copy any locally-built wheels from `result/`
3. Rename all to `gtsam_extended` with normalized version
4. Validate with `twine check`
5. Upload to PyPI
6. Git-tag the version

## Manual Steps

```bash
# 1. Build local wheels (e.g. cp310)
nix build .#gtsam-wheel-cp310

# 2. Download existing wheels + collect local builds
python download_wheels.py

# 3. Rename all to gtsam_extended
python rename_wheel.py

# 4. Validate
twine check renamed_wheels/*.whl

# 5. Upload
twine upload renamed_wheels/*.whl
```

## User Experience

```bash
pip install gtsam-extended
```

```python
import gtsam
```

Works on macOS (arm64, x86_64), Linux (x86_64, aarch64/Jetson), Python 3.10-3.14.

## Versioning

The published version tracks upstream automatically. `run/upstream_version.py` is the single source of truth: it queries PyPI for the latest `gtsam-develop` build and derives our distribution version.

Upstream ships timestamped dev builds (e.g. `4.3a1.dev202605270118`). A `.dev` segment makes pip treat a release as a pre-release, so we fold the timestamp into a post-release instead:

```
upstream  4.3a1.dev202605270118  ->  extended  4.3a1.post202605270118
```

That keeps the result a normal, installable-by-default release while uniquely tracking each upstream build — so "did upstream change?" is a simple string comparison.

`rename_wheel.py` resolves the version in this order:

1. `TARGET_VERSION` env var (`./run/publish` exports this so download + rename agree)
2. derived from upstream `gtsam-develop` (the default — auto-tracks releases)
3. `pyproject.toml` (offline fallback only)

So a normal `./run/publish` already picks up new upstream releases — no manual version bump needed. To pin a specific upstream build, set `UPSTREAM_VERSION=...` (honored by both the version logic and the downloader).

## Continuous Updates (GitHub Actions)

Two workflows keep the package in sync with upstream:

- **`.github/workflows/auto-update.yml`** — runs daily (and on demand). It compares the upstream-derived target version against the published `gtsam-extended` version; if they differ, it calls the publish workflow.
- **`.github/workflows/publish.yml`** — runs on a `macos-14` (arm64) runner: installs Nix, builds the cp310 macOS-arm64 wheel (the only one upstream doesn't ship), downloads the rest from PyPI, renames everything to `gtsam-extended`, and uploads with `--skip-existing`. Also runnable manually from the Actions tab (with an optional "skip upload" dry-run input).

**Required secret:** add a PyPI API token as the repo secret `PYPI_TOKEN` (Settings → Secrets and variables → Actions). The publish workflow uses it as the twine password.
