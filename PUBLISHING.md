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

## Version Bumping

1. Update `version` in `pyproject.toml` (e.g., `4.3a1.post2`)
2. Optionally rebuild local wheels: `nix build .#gtsam-wheel-cp310`
3. Publish: `./run/publish`

The rename script reads the version from `pyproject.toml` and normalizes all wheels to that version.
