#!/usr/bin/env python3
"""Single source of truth for the upstream GTSAM version.

Queries PyPI for the latest gtsam-develop release so our republished
gtsam-extended automatically tracks upstream instead of pinning a hardcoded
version. Importable (rename/publish use the functions) and runnable.

Usage:
    upstream_version.py            # upstream version, e.g. 4.3a1.dev202605270118
    upstream_version.py --target   # our dist version, e.g. 4.3a1.post202605270118
    upstream_version.py --tag      # git tag, e.g. v4.3a1.post202605270118

Env overrides (for pinning / reproducibility):
    UPSTREAM_VERSION   pin the upstream version instead of querying PyPI
    POST_RELEASE       post number used only when upstream has no .devN segment
                       (default 1)

Versioning scheme
-----------------
Upstream publishes timestamped dev builds (e.g. 4.3a1.dev202605270118) that
change nightly. A ".dev" segment makes pip treat the release as a pre-release
(needs --pre), so we can't republish it verbatim. Instead we fold the dev
timestamp into a post-release number:

    4.3a1.dev202605270118  ->  4.3a1.post202605270118

That keeps the result a normal (installable-by-default) release while still
uniquely tracking each upstream build, so "did upstream change?" is a simple
string comparison against the published gtsam-extended version.
"""

import json
import os
import re
import sys
import urllib.request

UPSTREAM_PACKAGE = "gtsam-develop"


def upstream_version():
    pinned = os.environ.get("UPSTREAM_VERSION")
    if pinned:
        return pinned
    url = f"https://pypi.org/pypi/{UPSTREAM_PACKAGE}/json"
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)["info"]["version"]


def target_version(version=None):
    """Map an upstream version to our gtsam-extended distribution version."""
    version = version or upstream_version()
    # Fold a trailing .devN timestamp into a post-release number.
    match = re.match(r"^(?P<base>.+?)\.dev(?P<dev>\d+)$", version)
    if match:
        return f"{match.group('base')}.post{match.group('dev')}"
    # Clean upstream release (no .dev): append a post number so we can
    # republish without colliding with upstream's own version namespace.
    post = os.environ.get("POST_RELEASE", "1")
    return f"{version}.post{post}"


def git_tag(version=None):
    return "v" + target_version(version)


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    version = upstream_version()
    if arg == "--tag":
        print(git_tag(version))
    elif arg == "--target":
        print(target_version(version))
    elif arg in ("", "--version"):
        print(version)
    else:
        print(f"Unknown argument: {arg}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
