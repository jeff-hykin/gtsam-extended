#!/usr/bin/env python3
"""Bundle non-system dylibs into a wheel's .dylibs/ directory.

Usage: bundle_dylibs.py <so_dir> <dylib_dir> <gtsam_lib_dir>

Rewrites Mach-O load commands so the wheel is self-contained.
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SYSTEM_LIB_PREFIXES = ("/usr/lib/", "/System/")


def otool_deps(path: str) -> list[tuple[str, str]]:
    """Return list of (install_name, raw_line) for a Mach-O binary."""
    result = subprocess.run(
        ["otool", "-L", path], capture_output=True, text=True
    )
    deps = []
    for line in result.stdout.strip().splitlines()[1:]:  # skip first line (binary name)
        line = line.strip()
        match = re.match(r"^(\S+)", line)
        if match:
            deps.append((match.group(1), line))
    return deps


def otool_rpaths(path: str) -> list[str]:
    """Return list of LC_RPATH entries."""
    result = subprocess.run(
        ["otool", "-l", path], capture_output=True, text=True
    )
    rpaths = []
    lines = result.stdout.splitlines()
    for i, line in enumerate(lines):
        if "LC_RPATH" in line:
            for j in range(i + 1, min(i + 4, len(lines))):
                m = re.match(r"\s+path\s+(\S+)", lines[j])
                if m:
                    rpaths.append(m.group(1))
    return rpaths


def change_install_name(binary: str, old: str, new: str):
    """Change a load command in a Mach-O binary."""
    subprocess.run(
        ["install_name_tool", "-change", old, new, binary],
        check=True,
    )


def set_install_id(binary: str, new_id: str):
    """Set the install name (ID) of a dylib."""
    subprocess.run(
        ["install_name_tool", "-id", new_id, binary],
        check=True,
    )


def delete_rpath(binary: str, rpath: str):
    """Delete an LC_RPATH from a binary."""
    subprocess.run(
        ["install_name_tool", "-delete_rpath", rpath, binary],
        capture_output=True,  # ignore errors for missing rpaths
    )


def codesign(path: str):
    """Ad-hoc codesign a binary (optional, may not be available in Nix sandbox)."""
    try:
        subprocess.run(
            ["codesign", "--force", "--sign", "-", path],
            capture_output=True,
        )
    except FileNotFoundError:
        pass  # codesign not available in Nix sandbox, skip


def is_system_lib(path: str) -> bool:
    return any(path.startswith(p) for p in SYSTEM_LIB_PREFIXES)


def main():
    so_dir = Path(sys.argv[1])
    dylib_dir = Path(sys.argv[2])
    gtsam_lib_dir = Path(sys.argv[3])

    bundled: set[str] = set()  # lib names already bundled

    def resolve_rpath_lib(name: str) -> str | None:
        """Try to find a library by name in gtsam's lib dir."""
        candidates = list(gtsam_lib_dir.glob(name))
        if candidates:
            return str(candidates[0])
        return None

    def bundle(src_path: str, lib_name: str | None = None):
        """Copy a dylib into .dylibs/ and recursively bundle its deps."""
        if is_system_lib(src_path):
            return
        if lib_name is None:
            lib_name = os.path.basename(src_path)
        if lib_name in bundled:
            return

        dest = dylib_dir / lib_name
        print(f"  Bundling: {src_path} -> {dest}")
        shutil.copy2(src_path, dest)
        os.chmod(dest, 0o755)
        bundled.add(lib_name)

        # Set the ID
        set_install_id(str(dest), f"@loader_path/{lib_name}")

        # Recursively bundle deps of this dylib
        for dep_path, _ in otool_deps(str(dest)):
            if dep_path.startswith("/nix/store/"):
                dep_name = os.path.basename(dep_path)
                bundle(dep_path, dep_name)
                change_install_name(str(dest), dep_path, f"@loader_path/{dep_name}")
            elif dep_path.startswith("@rpath/"):
                dep_name = os.path.basename(dep_path)
                actual = resolve_rpath_lib(dep_name)
                if actual:
                    bundle(actual, dep_name)
                change_install_name(str(dest), dep_path, f"@loader_path/{dep_name}")

        # Remove rpaths
        for rp in otool_rpaths(str(dest)):
            delete_rpath(str(dest), rp)

    # Process each .so file
    for so_file in so_dir.glob("*.so"):
        print(f"\nProcessing: {so_file}")
        deps = otool_deps(str(so_file))

        for dep_path, raw_line in deps:
            dep_name = os.path.basename(dep_path)

            if dep_path.startswith("/nix/store/"):
                bundle(dep_path, dep_name)
                change_install_name(str(so_file), dep_path, f"@loader_path/.dylibs/{dep_name}")

            elif dep_path.startswith("@rpath/"):
                actual = resolve_rpath_lib(dep_name)
                if actual:
                    bundle(actual, dep_name)
                change_install_name(str(so_file), dep_path, f"@loader_path/.dylibs/{dep_name}")

            # System libs (/usr/lib/*, /System/*): leave as-is

        # Remove rpaths from the .so
        for rp in otool_rpaths(str(so_file)):
            delete_rpath(str(so_file), rp)

    # Re-sign everything
    for f in dylib_dir.iterdir():
        if f.is_file():
            codesign(str(f))
    for f in so_dir.glob("*.so"):
        codesign(str(f))

    print("\nDone bundling dylibs.")


if __name__ == "__main__":
    main()
