# Cutver Plugin Registry

This registry is a small, declarative index of Cutver plugins. Each plugin gets
one entry file that points at the released `.wasm` binary and pins the SHA-256
digest that Cutver checks before loading it. The Cutver CLI reads this index to
resolve `cutver plugin add <name>`.

The registry holds metadata only. Plugin source code lives in the author's own
repository; official plugins live in `cutver/plugins`. Nothing here is a build
input, so a plugin can ship without this repository changing its code.

## Who it is for

| Reader | Why they are here |
| --- | --- |
| Cutver users | Install a plugin by name and trust the pinned digest. |
| Plugin authors | Publish an entry that points at their released `.wasm`. |
| Maintainers | Review one small, uniform file per plugin. |

## The entry format

One TOML file per plugin at `plugins/<name>.toml`. The file stem must equal
`name`, so `plugins/github-releases.toml` declares `name = "github-releases"`.

```toml
name = "github-releases"
description = "Renders release notes grouped by conventional commit type."
author = "cutver"
tier = "official"
repository = "https://github.com/cutver/plugins"
capabilities = ["changelog.v1"]

[[release]]
version = "0.1.0"
url = "https://github.com/cutver/plugins/releases/download/github-releases-v0.1.0/github-releases.wasm"
sha256 = "0000000000000000000000000000000000000000000000000000000000000000"
```

Top-level fields:

| Field | Rule |
| --- | --- |
| `name` | Non-empty; ASCII letters, digits, hyphens and underscores; equals the file name. |
| `description` | Non-empty one-line summary. |
| `author` | Non-empty publisher name. |
| `repository` | Non-empty `https://` URL for the source. |
| `tier` | One of `official`, `verified`, `community`. |
| `capabilities` | One or more values from the closed set below. |
| `release` | One or more release tables. |

`capabilities` draws from the closed Cutver set:

| Capability | Operation | Purpose |
| --- | --- | --- |
| `changelog.v1` | `render` | Format release notes from the request Cutver supplies. |
| `manifest.v1` | `read`, `write` | Read or update a project manifest format. |
| `lifecycle.v1` | hooks | Run transactional work around bump and release. |
| `versioning.v1` | `compute` | Derive a version with a custom scheme. |

Each `[[release]]` table pins one published build:

| Field | Rule |
| --- | --- |
| `version` | Semver, for example `0.1.0` or `0.2.0-rc.1`. Unique within the entry. |
| `url` | `https://` URL whose path ends in `.wasm`. |
| `sha256` | Exactly 64 lowercase hexadecimal characters. |

## What the tiers mean

| Tier | Meaning |
| --- | --- |
| `official` | Maintained in `cutver/plugins` by the Cutver maintainers. |
| `verified` | Third-party. A maintainer has reviewed the source and the published artifacts. |
| `community` | Third-party. Indexed as-is, with no review or endorsement. |

`community` is not a warning label, it is a statement of what happened: nothing
was reviewed. Treat the pinned digest as the only guarantee, and read the source
before you install.

## Submit an entry

1. Fork this repository.
2. Release the plugin so the `.wasm` and its `.sha256` sidecar exist on a tag.
3. Add `plugins/<name>.toml`, using the digest from that release.
4. Open a pull request.
5. CI validates the fixture suite and the real entries; fix anything it reports.
6. A maintainer reviews and merges.

Before opening the pull request, run the same checks locally:

```sh
bash scripts/test_validate.sh
python3 scripts/validate.py plugins/*.toml
```

Contributor checklist:

- [ ] The file name equals the `name` field.
- [ ] `tier` and every `capabilities` value come from the allowed sets.
- [ ] Every release `url` ends in `.wasm` and starts with `https://`.
- [ ] Every `sha256` is 64 lowercase hex characters copied from the release.
- [ ] No two releases in the entry share a `version`.

## The digest pins one exact build

The `sha256` value identifies one specific `.wasm` binary, not the plugin in
general. Rebuild the same source and you get a different binary and a different
digest, because the plugin toolchain tracks `stable` rather than an exact
version. Re-release a plugin and the published bytes change too.

That means every new release needs its own entry update. Copy the digest from
the `.sha256` sidecar attached to that exact release; do not reuse a digest from
an earlier release, a local build, or another platform. If the digest and the
downloaded artifact disagree, Cutver refuses to load the plugin, which is the
intended behavior.

## Repository layout

| Path | Contents |
| --- | --- |
| `plugins/` | One entry file per plugin. Empty is valid. |
| `scripts/` | The validator and its fixture test. |
| `tests/fixtures/` | Known-valid and known-invalid entries. |
| `.github/workflows/` | CI that runs the validator. |

## Validate an empty registry

The registry is valid while `plugins/` holds no entries, and it becomes useful
the moment the first one lands. With no arguments, or with no matching files,
the validator prints that the registry is empty and exits 0.

## License

MIT. See the license file for the full text.
