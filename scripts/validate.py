#!/usr/bin/env python3
"""Validate Cutver registry entry files.

Each entry lives at ``plugins/<name>.toml`` and declares where a plugin's
``.wasm`` binary is published plus the SHA-256 digest that pins it. This script
takes entry file paths as arguments, reports every problem it finds in each
file, and exits non-zero when any entry is invalid. It uses only the Python
standard library and performs no network access.
"""

from __future__ import annotations

import glob
import re
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_TIERS = ("official", "verified", "community")
ALLOWED_CAPABILITIES = ("manifest.v1", "lifecycle.v1", "changelog.v1", "versioning.v1")

NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
GLOB_MAGIC_RE = re.compile(r"[*?[]")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
# The canonical semver.org grammar, anchored.
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def _is_nonempty_str(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _is_https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _validate_repository(path: Path, value: object, errors: list[str]) -> None:
    if not _is_nonempty_str(value):
        errors.append(f"{path}: repository: expected a non-empty https:// URL")
    elif not _is_https_url(value):
        errors.append(
            f"{path}: repository: expected an https:// URL, found {value!r}"
        )


def _validate_release(path: Path, index: int, release: object, errors: list[str]) -> str | None:
    """Validate one [[release]] table and return its version when valid."""
    prefix = f"{path}: release[{index}]"
    if not isinstance(release, dict):
        errors.append(f"{prefix}: expected a table with version, url and sha256")
        return None

    version: str | None = None
    raw_version = release.get("version")
    if not _is_nonempty_str(raw_version):
        errors.append(
            f"{prefix}.version: expected a non-empty semver string, "
            f"found {raw_version!r}"
        )
    elif not SEMVER_RE.match(raw_version):
        errors.append(
            f"{prefix}.version: expected a semver like 0.1.0, found {raw_version!r}"
        )
    else:
        version = raw_version

    raw_url = release.get("url")
    if not _is_nonempty_str(raw_url):
        errors.append(
            f"{prefix}.url: expected a non-empty https:// URL ending in .wasm"
        )
    elif not _is_https_url(raw_url):
        errors.append(
            f"{prefix}.url: expected an https:// URL, found {raw_url!r}"
        )
    elif not urlparse(raw_url).path.endswith(".wasm"):
        errors.append(
            f"{prefix}.url: expected a URL whose path ends in .wasm, "
            f"found {raw_url!r}"
        )

    raw_sha = release.get("sha256")
    if not _is_nonempty_str(raw_sha):
        errors.append(
            f"{prefix}.sha256: expected 64 lowercase hexadecimal characters"
        )
    elif not SHA256_RE.match(raw_sha):
        errors.append(
            f"{prefix}.sha256: expected 64 lowercase hexadecimal characters, "
            f"found {raw_sha!r}"
        )

    return version


def validate_entry(path: Path, data: dict) -> list[str]:
    """Return every validation problem found in a parsed entry, if any."""
    errors: list[str] = []

    name = data.get("name")
    if not _is_nonempty_str(name):
        errors.append(f"{path}: name: expected a non-empty string")
    else:
        if not NAME_RE.match(name):
            errors.append(
                f"{path}: name: expected only ASCII letters, digits, hyphens "
                f"and underscores, found {name!r}"
            )
        if name != path.stem:
            errors.append(
                f"{path}: name: expected {path.stem!r} (the file name) but "
                f"found {name!r}"
            )

    if not _is_nonempty_str(data.get("description")):
        errors.append(f"{path}: description: expected a non-empty string")

    if not _is_nonempty_str(data.get("author")):
        errors.append(f"{path}: author: expected a non-empty string")

    _validate_repository(path, data.get("repository"), errors)

    tier = data.get("tier")
    if not _is_nonempty_str(tier):
        errors.append(
            f"{path}: tier: expected one of {', '.join(ALLOWED_TIERS)}"
        )
    elif tier not in ALLOWED_TIERS:
        errors.append(
            f"{path}: tier: expected one of {', '.join(ALLOWED_TIERS)}, "
            f"found {tier!r}"
        )

    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        errors.append(
            f"{path}: capabilities: expected a non-empty list drawn from "
            f"{', '.join(ALLOWED_CAPABILITIES)}"
        )
    else:
        for capability in capabilities:
            if not isinstance(capability, str) or capability not in ALLOWED_CAPABILITIES:
                errors.append(
                    f"{path}: capabilities: expected only "
                    f"{', '.join(ALLOWED_CAPABILITIES)}, found {capability!r}"
                )

    releases = data.get("release")
    if not isinstance(releases, list) or not releases:
        errors.append(
            f"{path}: release: expected at least one [[release]] table"
        )
        return errors

    seen_versions: dict[str, int] = {}
    for index, release in enumerate(releases):
        version = _validate_release(path, index, release, errors)
        if version is None:
            continue
        if version in seen_versions:
            errors.append(
                f"{path}: release[{index}].version: duplicate version {version!r} "
                f"already declared at release[{seen_versions[version]}]"
            )
        else:
            seen_versions[version] = index

    return errors


def _expand_arguments(arguments: list[str]) -> list[Path]:
    """Expand glob patterns; keep plain paths literal so typos still error."""
    paths: list[Path] = []
    for argument in arguments:
        if GLOB_MAGIC_RE.search(argument):
            paths.extend(Path(match) for match in sorted(glob.glob(argument)))
        else:
            paths.append(Path(argument))
    return paths


def main(argv: list[str]) -> int:
    paths = _expand_arguments(argv[1:])
    if not paths:
        print("No entries to validate: the registry is empty.")
        return 0

    failed = 0
    for path in paths:
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except FileNotFoundError:
            print(f"{path}: error: file not found")
            failed += 1
            continue
        except tomllib.TOMLDecodeError as exc:
            print(f"{path}: error: invalid TOML: {exc}")
            failed += 1
            continue

        errors = validate_entry(path, data)
        if errors:
            failed += 1
            for error in errors:
                print(error)

    if failed:
        print(f"{failed} of {len(paths)} entries failed validation.")
        return 1

    print(f"Validated {len(paths)} entries successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
