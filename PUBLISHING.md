# Publishing to PyPI

This package uploads the macOS arm64 GTSAM wheel to PyPI under the distribution name `gtsam-macos`.

## What Gets Uploaded

One wheel file (currently):
- `gtsam_macos-4.3a1-cp312-cp312-macosx_14_0_arm64.whl`

The wheel:
- Is ~27 MB (well under PyPI's 100 MB limit)
- Contains the `gtsam` package (so `import gtsam` works)
- Has distribution name `gtsam-macos` (so it doesn't conflict with the official `gtsam` package)
- Bundles all non-system dylibs (boost, tbb, metis, etc.)

## Prerequisites

1. Build the wheel first:
   ```bash
   nix build
   ```

2. Ensure `twine` is available (it's in the nix dev shell):
   ```bash
   nix develop
   ```

3. Have a `~/.pypirc` configured with your PyPI credentials, or be ready to enter them interactively.

## Publishing

```bash
./run/publish
```

This will:
1. Run `rename_wheel.py` to rename `gtsam` -> `gtsam_macos` distribution name
2. Validate the wheel with `twine check`
3. Upload to PyPI
4. Tag the git version

## Manual Publishing

If you prefer to do it manually:

```bash
# 1. Rename the wheel
python rename_wheel.py

# 2. Validate
twine check renamed_wheels/*.whl

# 3. Upload
twine upload renamed_wheels/*.whl
```

## User Experience

After publishing, users can:

```bash
pip install gtsam-macos
import gtsam
```

## Version Bumping

To publish a new version:
1. Update `version` in `pyproject.toml` (e.g., `4.3a1.post2`)
2. Rebuild: `nix build`
3. Publish: `./run/publish`

Note: The wheel's internal version comes from GTSAM's build (4.3a1). The `.postN` suffix in pyproject.toml is for tracking our packaging iterations.
