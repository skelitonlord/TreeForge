from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


class AndroidProviderReleaseError(RuntimeError):
    pass


_LOCK_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "android"
    / "provider-releases.json"
)

_CACHE_MARKER = ".treeforge-release.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)
    return digest.hexdigest()


def _load_lock() -> dict[str, Any]:
    try:
        data = json.loads(_LOCK_PATH.read_text())
    except Exception as exc:
        raise AndroidProviderReleaseError(
            f"unable to read provider release lock: "
            f"{_LOCK_PATH}: {exc}"
        ) from exc

    if data.get("schema") != 1:
        raise AndroidProviderReleaseError(
            "unsupported provider release lock schema"
        )

    providers = data.get("providers")
    if not isinstance(providers, dict):
        raise AndroidProviderReleaseError(
            "provider release lock has no providers map"
        )

    return data


def provider_release_record(
    name: str,
) -> dict[str, Any]:
    data = _load_lock()
    try:
        record = data["providers"][name]
    except KeyError as exc:
        raise AndroidProviderReleaseError(
            f"unknown published provider: {name}"
        ) from exc

    return dict(record)


def provider_release_lock_metadata() -> dict[str, Any]:
    """
    Return public-release metadata for the pinned Android provider set.

    The source repository is provenance only. Normal provider
    materialization uses the public release repository.
    """

    data = _load_lock()

    return {
        "schema": data["schema"],
        "public_repository":
            data["public_repository"],
        "source_repository":
            data["source_repository"],
        "source_commit":
            data["source_commit"],
    }


def _provider_source_commit(
    record: dict[str, Any],
    lock: dict[str, Any] | None = None,
) -> str:
    value = record.get(
        "source_commit"
    )

    if value is None:
        if lock is None:
            lock = _load_lock()

        value = lock.get(
            "source_commit"
        )

    if (
        not isinstance(value, str)
        or len(value) != 40
        or any(
            character
            not in "0123456789abcdef"
            for character in value
        )
    ):
        name = record.get(
            "_name",
            record.get(
                "name",
                "<unknown>",
            ),
        )

        raise AndroidProviderReleaseError(
            f"{name}: invalid pinned source commit: "
            f"{value!r}"
        )

    return value


def _default_cache_root() -> Path:
    explicit = (
        os.environ.get(
            "TREEFORGE_ANDROID_PROVIDER_CACHE_ROOT"
        )
        or os.environ.get(
            "TREEFORGE_ANDROID_HOST_PROVIDER_CACHE_ROOT"
        )
    )

    if explicit:
        return Path(explicit).expanduser().resolve()

    xdg = os.environ.get("XDG_CACHE_HOME")
    base = (
        Path(xdg).expanduser()
        if xdg
        else Path.home() / ".cache"
    )

    return (
        base
        / "treeforge"
        / "android-provider"
    ).resolve()


def _cache_destination(
    *,
    name: str,
    release: str,
    cache_root: Path | None,
) -> Path:
    root = (
        cache_root.resolve()
        if cache_root is not None
        else _default_cache_root()
    )
    return root / name / release


def _cache_is_current(
    destination: Path,
    record: dict[str, Any],
) -> bool:
    marker_path = destination / _CACHE_MARKER
    manifest_path = destination / "manifest.json"

    if (
        not destination.is_dir()
        or not marker_path.is_file()
        or not manifest_path.is_file()
    ):
        return False

    try:
        marker = json.loads(
            marker_path.read_text()
        )
    except Exception:
        return False

    return (
        marker.get("provider")
        == marker.get("name")
        == record.get("_name")
        and marker.get("release")
        == record.get("release")
        and marker.get("release_tag")
        == record.get("release_tag")
        and marker.get("archive_sha256")
        == record.get("archive_sha256")
    )


def _safe_extract(
    archive: Path,
    destination: Path,
) -> None:
    destination = destination.resolve()

    with tarfile.open(
        archive,
        mode="r:xz",
    ) as tar:
        members = tar.getmembers()

        for member in members:
            name = member.name

            if (
                not name
                or name.startswith("/")
            ):
                raise AndroidProviderReleaseError(
                    f"unsafe archive member: {name!r}"
                )

            parts = Path(name).parts

            if ".." in parts:
                raise AndroidProviderReleaseError(
                    f"archive traversal member: {name!r}"
                )

            if member.issym() or member.islnk():
                raise AndroidProviderReleaseError(
                    f"archive link member rejected: "
                    f"{name!r}"
                )

            target = (
                destination / name
            ).resolve()

            try:
                target.relative_to(destination)
            except ValueError as exc:
                raise AndroidProviderReleaseError(
                    f"archive member escapes root: "
                    f"{name!r}"
                ) from exc

        tar.extractall(
            destination,
            members=members,
        )


def _package_root(
    extracted: Path,
) -> Path:
    direct = extracted / "RELEASE.json"

    if direct.is_file():
        return extracted

    matches = sorted(
        extracted.rglob("RELEASE.json")
    )

    if len(matches) != 1:
        raise AndroidProviderReleaseError(
            "release archive must contain exactly one "
            "RELEASE.json"
        )

    return matches[0].parent


def _verify_internal_sha256(
    package_root: Path,
) -> None:
    sums_path = package_root / "SHA256SUMS"

    if not sums_path.is_file():
        raise AndroidProviderReleaseError(
            "release archive has no SHA256SUMS"
        )

    listed: set[str] = set()

    for raw in sums_path.read_text().splitlines():
        line = raw.strip()

        if not line:
            continue

        pieces = line.split(maxsplit=1)

        if len(pieces) != 2:
            raise AndroidProviderReleaseError(
                f"invalid SHA256SUMS line: {raw!r}"
            )

        expected, relative = pieces

        relative = relative.lstrip("* ")
        path = package_root / relative

        if not path.is_file():
            raise AndroidProviderReleaseError(
                "SHA256SUMS references missing file: "
                f"{relative}"
            )

        actual = _sha256(path)

        if actual != expected:
            raise AndroidProviderReleaseError(
                f"internal SHA mismatch: {relative}: "
                f"expected={expected} actual={actual}"
            )

        listed.add(relative)

    if not listed:
        raise AndroidProviderReleaseError(
            "release SHA256SUMS is empty"
        )


def _download(
    *,
    repository: str,
    tag: str,
    asset: str,
    destination: Path,
) -> None:
    local_root = os.environ.get(
        "TREEFORGE_ANDROID_PROVIDER_RELEASE_ASSET_ROOT"
    ) or os.environ.get(
        "TREEFORGE_ANDROID_HOST_PROVIDER_RELEASE_ASSET_ROOT"
    )

    if local_root:
        source = (
            Path(local_root)
            .expanduser()
            .resolve()
            / asset
        )

        if not source.is_file():
            raise AndroidProviderReleaseError(
                f"local release asset missing: {source}"
            )

        shutil.copy2(
            source,
            destination,
        )
        return

    if os.environ.get(
        "TREEFORGE_ANDROID_PROVIDER_OFFLINE"
    ) == "1" or os.environ.get(
        "TREEFORGE_ANDROID_HOST_PROVIDER_OFFLINE"
    ) == "1":
        raise AndroidProviderReleaseError(
            "provider cache miss while offline"
        )

    tag_path = urllib.parse.quote(
        tag,
        safe="/",
    )

    asset_path = urllib.parse.quote(
        asset,
        safe="",
    )

    url = (
        f"https://github.com/{repository}"
        f"/releases/download/{tag_path}/{asset_path}"
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "TreeForge-provider-resolver/1",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            with destination.open("wb") as stream:
                shutil.copyfileobj(
                    response,
                    stream,
                )
    except urllib.error.URLError as exc:
        raise AndroidProviderReleaseError(
            f"unable to download provider asset: "
            f"{url}: {exc}"
        ) from exc


def _identity_check(
    *,
    package_root: Path,
    name: str,
    record: dict[str, Any],
) -> None:
    release_path = package_root / "RELEASE.json"
    rebuild_path = package_root / "SOURCE-REBUILD.json"

    if not release_path.is_file():
        raise AndroidProviderReleaseError(
            "release archive has no RELEASE.json"
        )

    if not rebuild_path.is_file():
        raise AndroidProviderReleaseError(
            "release archive has no SOURCE-REBUILD.json"
        )

    release = json.loads(
        release_path.read_text()
    )

    rebuild = json.loads(
        rebuild_path.read_text()
    )

    if release.get("provider") != name:
        raise AndroidProviderReleaseError(
            f"release provider mismatch for {name}"
        )

    if (
        release.get("release_tag")
        != record["release_tag"]
    ):
        raise AndroidProviderReleaseError(
            f"release tag mismatch for {name}"
        )

    if rebuild.get("provider") != name:
        raise AndroidProviderReleaseError(
            f"SOURCE-REBUILD provider mismatch "
            f"for {name}"
        )


def _build_hash_index(
    package_root: Path,
) -> dict[str, list[Path]]:
    result: dict[str, list[Path]] = {}

    for path in package_root.rglob("*"):
        if not path.is_file():
            continue

        digest = _sha256(path)

        result.setdefault(
            digest,
            [],
        ).append(path)

    return result


def _manifest_file_records(
    manifest: dict[str, Any],
) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []

    for value in manifest.values():
        if not isinstance(value, list):
            continue

        for item in value:
            if not isinstance(item, dict):
                continue

            path = item.get("path")
            digest = item.get("sha256")

            if (
                isinstance(path, str)
                and path
                and isinstance(digest, str)
                and len(digest) == 64
            ):
                records.append(
                    {
                        "path": path,
                        "sha256": digest,
                    }
                )

    unique: dict[
        tuple[str, str],
        dict[str, str],
    ] = {}

    for item in records:
        unique[
            (
                item["path"],
                item["sha256"],
            )
        ] = item

    return list(unique.values())


def _normalize_consumer_package(
    *,
    package_root: Path,
    destination: Path,
    name: str,
    record: dict[str, Any],
) -> None:
    consumer_manifest = (
        package_root
        / "consumer"
        / "manifest.json"
    )

    if not consumer_manifest.is_file():
        raise AndroidProviderReleaseError(
            f"{name}: release is missing "
            "consumer/manifest.json"
        )

    manifest = json.loads(
        consumer_manifest.read_text()
    )

    hash_index = _build_hash_index(
        package_root
    )

    file_records = _manifest_file_records(
        manifest
    )

    if not file_records:
        raise AndroidProviderReleaseError(
            f"{name}: normalized consumer "
            "manifest has no file records"
        )

    for item in file_records:
        relative = item["path"]
        expected = item["sha256"]

        candidates = (
            package_root / relative,
            package_root / "payload" / relative,
        )

        source: Path | None = None

        for candidate in candidates:
            if (
                candidate.is_file()
                and _sha256(candidate)
                == expected
            ):
                source = candidate
                break

        if source is None:
            matches = hash_index.get(
                expected,
                [],
            )

            if len(matches) != 1:
                raise AndroidProviderReleaseError(
                    f"{name}: cannot uniquely map "
                    f"{relative} by SHA-256 "
                    f"(matches={len(matches)})"
                )

            source = matches[0]

        target = destination / relative
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            target,
        )

    shutil.copy2(
        consumer_manifest,
        destination / "manifest.json",
    )

    marker = {
        "schema": 1,
        "name": name,
        "provider": name,
        "release": record["release"],
        "release_tag": record["release_tag"],
        "asset": record["asset"],
        "archive_sha256":
            record["archive_sha256"],
        "public_repository":
            _load_lock()["public_repository"],
        "source_repository":
            _load_lock()["source_repository"],
        "source_commit":
            _provider_source_commit(record),
    }

    (
        destination / _CACHE_MARKER
    ).write_text(
        json.dumps(
            marker,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _materialize_raw_package(
    *,
    package_root: Path,
    destination: Path,
    name: str,
    record: dict[str, Any],
) -> None:
    """
    Normalize a published runtime-provider archive.

    Release archives keep runtime payloads below ``payload/``.
    Existing TreeForge runtime bundle loaders expect the original
    provider layout directly below the provider root, with
    ``manifest.json`` alongside paths such as ``rootfs/...``.

    The published archive is already verified before this function:
    archive SHA-256, internal SHA256SUMS, RELEASE.json, and
    SOURCE-REBUILD.json have all passed.
    """

    release_manifest_path = (
        package_root / "manifest.json"
    )

    if not release_manifest_path.is_file():
        raise AndroidProviderReleaseError(
            f"{name}: runtime release has no manifest.json"
        )

    consumer_manifest_path = (
        package_root
        / "consumer"
        / "manifest.json"
    )

    if (
        record.get(
            "consumer_manifest_schema"
        )
        == 1
    ):
        if not consumer_manifest_path.is_file():
            raise AndroidProviderReleaseError(
                f"{name}: runtime consumer manifest "
                "is unavailable"
            )

        manifest_path = (
            consumer_manifest_path
        )
    else:
        manifest_path = (
            release_manifest_path
        )

    payload_root = package_root / "payload"

    if not payload_root.is_dir():
        raise AndroidProviderReleaseError(
            f"{name}: runtime release has no payload directory"
        )

    shutil.copytree(
        payload_root,
        destination,
        dirs_exist_ok=True,
    )

    shutil.copy2(
        manifest_path,
        destination / "manifest.json",
    )

    # Preserve release/source/legal metadata without making it part
    # of the runtime bundle's path namespace.
    metadata_root = destination / ".release-metadata"
    metadata_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        release_manifest_path,
        metadata_root
        / "release-manifest.json",
    )

    for entry in package_root.iterdir():
        if entry.name in {
            "payload",
            "consumer",
            "manifest.json",
        }:
            continue

        target = metadata_root / entry.name

        if entry.is_dir():
            shutil.copytree(
                entry,
                target,
                dirs_exist_ok=True,
            )
        elif entry.is_file():
            shutil.copy2(
                entry,
                target,
            )

    manifest = json.loads(
        manifest_path.read_text()
    )

    if (
        record.get(
            "consumer_manifest_schema"
        )
        == 1
    ):
        if (
            manifest.get("schema") != 1
            or manifest.get("name") != name
            or manifest.get("release")
            != record["release"]
        ):
            raise AndroidProviderReleaseError(
                f"{name}: invalid runtime "
                "consumer manifest identity"
            )

    records: list[tuple[str, str]] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            relative = value.get("path")
            digest = value.get("sha256")

            if (
                isinstance(relative, str)
                and relative
                and isinstance(digest, str)
                and len(digest) == 64
            ):
                records.append(
                    (
                        relative,
                        digest,
                    )
                )

            for child in value.values():
                collect(child)

        elif isinstance(value, list):
            for child in value:
                collect(child)

    if (
        record.get(
            "consumer_manifest_schema"
        )
        == 1
    ):
        runtime_files = manifest.get(
            "files"
        )

        if (
            not isinstance(
                runtime_files,
                list,
            )
            or not runtime_files
        ):
            raise AndroidProviderReleaseError(
                f"{name}: runtime consumer manifest "
                "files must be a non-empty list"
            )

        # Schema-1 runtime manifests may also contain compliance,
        # licensing and provenance records with their own path/SHA
        # pairs. Only the top-level files array describes material
        # that belongs in the normalized runtime provider root.
        collect(runtime_files)
    else:
        collect(manifest)

    unique = sorted(set(records))

    if not unique:
        raise AndroidProviderReleaseError(
            f"{name}: runtime manifest has no "
            "path/SHA-256 file records"
        )

    for relative, expected in unique:
        relative_path = Path(relative)

        if (
            relative_path.is_absolute()
            or ".." in relative_path.parts
        ):
            raise AndroidProviderReleaseError(
                f"{name}: unsafe runtime manifest path: "
                f"{relative}"
            )

        runtime_path = destination / relative_path

        if not runtime_path.is_file():
            raise AndroidProviderReleaseError(
                f"{name}: runtime manifest file missing: "
                f"{relative}"
            )

        actual = _sha256(
            runtime_path
        )

        if actual != expected:
            raise AndroidProviderReleaseError(
                f"{name}: runtime file SHA mismatch: "
                f"{relative}: "
                f"expected={expected} actual={actual}"
            )

    marker = {
        "schema": 1,
        "name": name,
        "provider": name,
        "release": record["release"],
        "release_tag": record["release_tag"],
        "asset": record["asset"],
        "archive_sha256":
            record["archive_sha256"],
        "public_repository":
            _load_lock()["public_repository"],
        "source_repository":
            _load_lock()["source_repository"],
        "source_commit":
            _provider_source_commit(record),
        "runtime_manifest_file_records":
            len(unique),
    }

    (
        destination / _CACHE_MARKER
    ).write_text(
        json.dumps(
            marker,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def materialize_android_provider(
    *,
    name: str,
    release: str,
    cache_root: Path | None = None,
) -> Path:
    lock = _load_lock()
    providers = lock["providers"]

    if name not in providers:
        raise AndroidProviderReleaseError(
            f"provider is not published: {name}"
        )

    record = dict(
        providers[name]
    )

    record["_name"] = name

    if record.get("release") != release:
        raise AndroidProviderReleaseError(
            f"{name}: release mismatch: "
            f"requested={release} "
            f"pinned={record.get('release')}"
        )

    destination = _cache_destination(
        name=name,
        release=release,
        cache_root=cache_root,
    )

    if _cache_is_current(
        destination,
        record,
    ):
        return destination

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory(
        prefix=f"treeforge-{name}-",
        dir=destination.parent,
    ) as temporary:
        temporary_root = Path(temporary)

        archive = (
            temporary_root
            / record["asset"]
        )

        _download(
            repository=lock[
                "public_repository"
            ],
            tag=record[
                "release_tag"
            ],
            asset=record[
                "asset"
            ],
            destination=archive,
        )

        actual_archive_sha = _sha256(
            archive
        )

        if (
            actual_archive_sha
            != record["archive_sha256"]
        ):
            raise AndroidProviderReleaseError(
                f"{name}: archive SHA mismatch: "
                f"expected="
                f"{record['archive_sha256']} "
                f"actual={actual_archive_sha}"
            )

        extracted = (
            temporary_root / "extracted"
        )

        extracted.mkdir()

        _safe_extract(
            archive,
            extracted,
        )

        package_root = _package_root(
            extracted
        )

        _verify_internal_sha256(
            package_root
        )

        _identity_check(
            package_root=package_root,
            name=name,
            record=record,
        )

        stage = (
            temporary_root
            / "normalized"
        )

        stage.mkdir()

        consumer_schema = record.get(
            "consumer_manifest_schema"
        )

        if record.get(
            "consumer_manifest"
        ):
            if consumer_schema == 2:
                _normalize_consumer_package(
                    package_root=package_root,
                    destination=stage,
                    name=name,
                    record=record,
                )
            elif consumer_schema == 1:
                _materialize_raw_package(
                    package_root=package_root,
                    destination=stage,
                    name=name,
                    record=record,
                )
            else:
                raise AndroidProviderReleaseError(
                    f"{name}: unsupported consumer "
                    f"manifest schema: "
                    f"{consumer_schema!r}"
                )
        else:
            _materialize_raw_package(
                package_root=package_root,
                destination=stage,
                name=name,
                record=record,
            )

        if destination.exists():
            shutil.rmtree(
                destination
            )

        shutil.copytree(
            stage,
            destination,
        )

    return destination


def materialize_android_host_provider(
    *,
    name: str,
    release: str,
    cache_root: Path | None = None,
) -> Path:
    record = provider_release_record(
        name
    )

    if (
        not record.get(
            "consumer_manifest"
        )
        or record.get(
            "consumer_manifest_schema"
        )
        != 2
    ):
        raise AndroidProviderReleaseError(
            f"{name}: provider is not a "
            "schema-2 normalized host consumer"
        )

    return materialize_android_provider(
        name=name,
        release=release,
        cache_root=cache_root,
    )


def verify_materialized_android_provider_root(
    root: Path,
) -> dict[str, Any]:
    """
    Verify that a materialized provider root belongs to the exact
    pinned TreeForge public-release set.

    Payload integrity remains the responsibility of the provider
    bundle loader. This check establishes release/cache identity for
    provider roots located outside TreeForge's source tree.
    """

    root = Path(root).expanduser().resolve()

    marker_path = root / _CACHE_MARKER

    if not marker_path.is_file():
        raise AndroidProviderReleaseError(
            "external provider root has no "
            f"{_CACHE_MARKER}: {root}"
        )

    if not (
        root / "manifest.json"
    ).is_file():
        raise AndroidProviderReleaseError(
            "external provider root has no "
            f"manifest.json: {root}"
        )

    try:
        marker = json.loads(
            marker_path.read_text()
        )
    except Exception as exc:
        raise AndroidProviderReleaseError(
            "unable to read provider cache marker: "
            f"{marker_path}: {exc}"
        ) from exc

    lock = _load_lock()

    name = marker.get("provider")

    if not isinstance(name, str) or not name:
        raise AndroidProviderReleaseError(
            "provider cache marker has no "
            "provider identity"
        )

    if marker.get("name") != name:
        raise AndroidProviderReleaseError(
            f"{name}: provider cache marker "
            "name/provider mismatch"
        )

    record = lock["providers"].get(name)

    if not isinstance(record, dict):
        raise AndroidProviderReleaseError(
            f"{name}: provider is not present "
            "in the pinned release lock"
        )

    expected = {
        "release":
            record["release"],
        "release_tag":
            record["release_tag"],
        "asset":
            record["asset"],
        "archive_sha256":
            record["archive_sha256"],
        "public_repository":
            lock["public_repository"],
        "source_repository":
            lock["source_repository"],
        "source_commit":
            _provider_source_commit(record, lock),
    }

    for key, value in expected.items():
        actual = marker.get(key)

        if actual != value:
            raise AndroidProviderReleaseError(
                f"{name}: provider cache marker "
                f"{key!r} mismatch: "
                f"expected={value!r} "
                f"actual={actual!r}"
            )

    return marker


__all__ = [
    "AndroidProviderReleaseError",
    "materialize_android_host_provider",
    "materialize_android_provider",
    "provider_release_record",
]
