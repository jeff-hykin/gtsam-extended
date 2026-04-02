#!/usr/bin/env python3
"""
Rename GTSAM wheel distribution name from 'gtsam' to 'gtsam_macos'.

This changes the distribution name (what PyPI sees) while keeping the
internal 'gtsam' package intact (so `import gtsam` still works).

This is the same approach used by numpy, torch, etc. for unofficial builds.
"""

import os
import re
import sys
import csv
import hashlib
import base64
import zipfile
import shutil
import tempfile
from pathlib import Path
from io import StringIO

OLD_DIST_NAME = "gtsam"
NEW_DIST_NAME = "gtsam_macos"


def hash_file(path):
    """Compute SHA256 hash in RECORD format (url-safe base64, no padding)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    digest = base64.urlsafe_b64encode(h.digest()).rstrip(b"=").decode("ascii")
    return f"sha256={digest}"


def rename_wheel(wheel_path, output_dir):
    wheel_path = Path(wheel_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse wheel filename
    # gtsam-4.3a1-cp312-cp312-macosx_14_0_arm64.whl
    parts = wheel_path.stem.split("-")
    version = parts[1]
    tags = "-".join(parts[2:])  # cp312-cp312-macosx_14_0_arm64

    new_wheel_name = f"{NEW_DIST_NAME}-{version}-{tags}.whl"

    old_dist_info = f"{OLD_DIST_NAME}-{version}.dist-info"
    new_dist_info = f"{NEW_DIST_NAME}-{version}.dist-info"

    # Unpack
    tmpdir = tempfile.mkdtemp()
    with zipfile.ZipFile(wheel_path, "r") as zf:
        zf.extractall(tmpdir)

    # Rename dist-info directory
    old_info_path = Path(tmpdir) / old_dist_info
    new_info_path = Path(tmpdir) / new_dist_info

    if not old_info_path.exists():
        print(f"ERROR: {old_dist_info} not found in wheel")
        sys.exit(1)

    old_info_path.rename(new_info_path)

    # Update METADATA: change Name field
    metadata_path = new_info_path / "METADATA"
    metadata = metadata_path.read_text()
    metadata = re.sub(
        r"^Name: gtsam$",
        f"Name: {NEW_DIST_NAME.replace('_', '-')}",
        metadata,
        flags=re.MULTILINE,
    )
    metadata_path.write_text(metadata)

    # Update WHEEL file if it references the old name
    wheel_meta_path = new_info_path / "WHEEL"
    if wheel_meta_path.exists():
        wheel_meta = wheel_meta_path.read_text()
        # Usually no changes needed, but just in case
        wheel_meta_path.write_text(wheel_meta)

    # Update top_level.txt if it exists (keep 'gtsam' since that's the importable package)
    top_level_path = new_info_path / "top_level.txt"
    if top_level_path.exists():
        # Keep as-is — the import name is still 'gtsam'
        pass

    # Rebuild RECORD
    record_path = new_info_path / "RECORD"
    record_lines = []

    for root, dirs, files in os.walk(tmpdir):
        for fname in files:
            fpath = Path(root) / fname
            arcname = str(fpath.relative_to(tmpdir))

            # RECORD itself gets no hash
            if arcname == str(Path(new_dist_info) / "RECORD"):
                continue

            file_hash = hash_file(fpath)
            file_size = fpath.stat().st_size
            record_lines.append(f"{arcname},{file_hash},{file_size}")

    # Add RECORD entry (no hash for itself)
    record_lines.append(f"{new_dist_info}/RECORD,,")
    record_path.write_text("\n".join(record_lines) + "\n")

    # Repack
    new_wheel_path = output_dir / new_wheel_name
    with zipfile.ZipFile(new_wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(tmpdir):
            for fname in files:
                fpath = Path(root) / fname
                arcname = str(fpath.relative_to(tmpdir))
                zf.write(fpath, arcname)

    shutil.rmtree(tmpdir)

    print(f"Renamed: {wheel_path.name} -> {new_wheel_name}")
    return new_wheel_path


def main():
    import glob

    # Find wheels in result/
    wheels = glob.glob("result/gtsam-*.whl")
    if not wheels:
        print("ERROR: No gtsam wheels found in result/")
        print("Run 'nix build' first to generate the wheel.")
        sys.exit(1)

    output_dir = Path("renamed_wheels")
    if output_dir.exists():
        shutil.rmtree(output_dir)

    for wheel in wheels:
        rename_wheel(wheel, output_dir)

    print(f"\nRenamed wheels in: {output_dir}/")
    for whl in sorted(output_dir.glob("*.whl")):
        size_mb = whl.stat().st_size / (1024 * 1024)
        print(f"  {whl.name}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
