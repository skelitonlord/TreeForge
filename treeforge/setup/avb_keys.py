from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import shutil
import stat
import subprocess


AVB_BRINGUP_PARTITIONS: tuple[
    str,
    ...,
] = (
    "boot",
    "init_boot",
    "vbmeta",
    "vbmeta_system",
    "vbmeta_vendor",
)


AVB_BRINGUP_KEY_BITS = {
    "boot": 2048,
    "init_boot": 2048,
    "vbmeta": 4096,
    "vbmeta_system": 2048,
    "vbmeta_vendor": 2048,
}

AVB_BRINGUP_PLATFORM_PROFILE = "android-15.0.0_r36"


@dataclass(
    frozen=True,
    slots=True,
)
class AvbBringupKey:
    partition: str
    persistent_path: Path
    deployed_path: Path | None
    public_key_sha256: str
    generated: bool


@dataclass(
    frozen=True,
    slots=True,
)
class AvbBringupKeyProvisioningResult:
    repository_root: Path
    aosp_root: Path
    device: str

    keys: tuple[
        AvbBringupKey,
        ...,
    ]

    @property
    def deployed(
        self,
    ) -> bool:
        return all(
            key.deployed_path
            is not None
            for key in self.keys
        )


def _openssl() -> str:
    executable = shutil.which(
        "openssl"
    )

    if executable is None:
        raise RuntimeError(
            "OpenSSL is required for TreeForge AVB "
            "bring-up key provisioning"
        )

    return executable


def _validate_rsa_bits(
    *,
    openssl: str,
    path: Path,
    bits: int,
) -> None:
    completed = subprocess.run(
        [
            openssl,
            "pkey",
            "-in",
            str(path),
            "-text",
            "-noout",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    output = (
        completed.stdout
        + "\n"
        + completed.stderr
    )

    marker = f"Private-Key: ({bits} bit"

    if marker not in output:
        raise RuntimeError(
            "TreeForge AVB development key has the wrong RSA size; "
            f"expected RSA-{bits}: {path}"
        )


def _public_fingerprint(
    *,
    openssl: str,
    path: Path,
) -> str:
    public_der = subprocess.run(
        [
            openssl,
            "pkey",
            "-in",
            str(path),
            "-pubout",
            "-outform",
            "DER",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout

    return sha256(
        public_der
    ).hexdigest()


def validate_avb_bringup_keys(
    *,
    repository_root: Path,
    device: str = "tangorpro",
) -> tuple[AvbBringupKey, ...]:
    """
    Validate one complete TreeForge development AVB keyset.

    This validation is entirely local. It does not inspect, require, or
    deploy into an AOSP checkout.
    """

    repository_root = (
        repository_root
        .expanduser()
        .resolve()
    )

    if not device:
        raise ValueError(
            "device must not be empty"
        )

    key_root = (
        repository_root
        / ".treeforge-private"
        / "keys"
        / "avb"
        / AVB_BRINGUP_PLATFORM_PROFILE
        / device
    )

    if not key_root.is_dir():
        raise RuntimeError(
            "TreeForge AVB development keyset is unavailable: "
            f"{key_root}"
        )

    expected_names = {
        f"{partition}.pem"
        for partition in AVB_BRINGUP_PARTITIONS
    }

    actual_names = {
        path.name
        for path in key_root.glob("*.pem")
    }

    if actual_names != expected_names:
        raise RuntimeError(
            "TreeForge AVB development key population does not "
            "match the platform profile; "
            f"expected={sorted(expected_names)!r}, "
            f"actual={sorted(actual_names)!r}"
        )

    openssl = _openssl()
    validated = []

    for partition in AVB_BRINGUP_PARTITIONS:
        path = (
            key_root
            / f"{partition}.pem"
        )

        if path.is_symlink():
            raise RuntimeError(
                "TreeForge AVB private key must not be a symlink: "
                f"{path}"
            )

        if not path.is_file():
            raise RuntimeError(
                "TreeForge AVB private key is unavailable: "
                f"{path}"
            )

        mode = stat.S_IMODE(
            path.stat().st_mode
        )

        if mode != 0o600:
            raise RuntimeError(
                "TreeForge AVB private key must have mode 0600: "
                f"{path} has {mode:04o}"
            )

        _validate_rsa_bits(
            openssl=openssl,
            path=path,
            bits=(
                AVB_BRINGUP_KEY_BITS[
                    partition
                ]
            ),
        )

        validated.append(
            AvbBringupKey(
                partition=partition,
                persistent_path=path,
                deployed_path=None,
                public_key_sha256=(
                    _public_fingerprint(
                        openssl=openssl,
                        path=path,
                    )
                ),
                generated=False,
            )
        )

    return tuple(validated)


def provision_avb_bringup_keys(
    *,
    repository_root: Path,
    aosp_root: Path | None = None,
    device: str = "tangorpro",
) -> AvbBringupKeyProvisioningResult:
    """
    Provision/reuse explicit TreeForge bring-up signing keys.

    Persistent private material belongs beneath .treeforge-private.

    If the TreeForge-generated device tree is already deployed into AOSP,
    copies of the persistent keys are placed where BoardConfig expects them.

    Private material must never be placed into frozen output/device-tree.
    """

    repository_root = (
        repository_root
        .expanduser()
        .resolve()
    )

    if aosp_root is None:
        aosp_root = (
            repository_root
            / "aosp"
        )

    aosp_root = (
        aosp_root
        .expanduser()
        .resolve()
    )

    if not device:
        raise ValueError(
            "device must not be empty"
        )

    openssl = _openssl()

    persistent_root = (
        repository_root
        / ".treeforge-private"
        / "keys"
        / "avb"
        / AVB_BRINGUP_PLATFORM_PROFILE
        / device
    )

    generated_output_key_root = (
        repository_root
        / "output"
        / "device-tree"
        / "device"
        / "treeforge"
        / device
        / "keys"
        / "avb"
    )

    if generated_output_key_root.is_dir():
        unexpected = tuple(
            sorted(
                generated_output_key_root.glob(
                    "*.pem"
                )
            )
        )

        if unexpected:
            raise RuntimeError(
                "private AVB keys must never be materialized "
                "inside frozen output/device-tree: "
                f"{unexpected!r}"
            )

    persistent_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    persistent_root.chmod(
        0o700
    )

    deployed_device_root = (
        aosp_root
        / "device"
        / "treeforge"
        / device
    )

    deployed_key_root = (
        deployed_device_root
        / "keys"
        / "avb"
    )

    deploy = (
        deployed_device_root.is_dir()
    )

    if deploy:
        deployed_key_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    results = []

    for partition in (
        AVB_BRINGUP_PARTITIONS
    ):
        expected_bits = (
            AVB_BRINGUP_KEY_BITS[
                partition
            ]
        )

        persistent = (
            persistent_root
            / f"{partition}.pem"
        )

        generated = False

        if not persistent.exists():
            subprocess.run(
                [
                    openssl,
                    "genpkey",
                    "-algorithm",
                    "RSA",
                    "-pkeyopt",
                    f"rsa_keygen_bits:{expected_bits}",
                    "-out",
                    str(
                        persistent
                    ),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            generated = True

        if not persistent.is_file():
            raise RuntimeError(
                "TreeForge AVB bring-up key path is not "
                f"a regular file: {persistent}"
            )

        persistent.chmod(
            0o600
        )

        _validate_rsa_bits(
            openssl=openssl,
            path=persistent,
            bits=expected_bits,
        )

        fingerprint = (
            _public_fingerprint(
                openssl=openssl,
                path=persistent,
            )
        )

        deployed: Path | None = None

        if deploy:
            deployed = (
                deployed_key_root
                / persistent.name
            )

            shutil.copy2(
                persistent,
                deployed,
            )

            deployed.chmod(
                0o600
            )

            if (
                persistent.read_bytes()
                != deployed.read_bytes()
            ):
                raise RuntimeError(
                    "deployed AVB bring-up key differs "
                    "from persistent private input: "
                    f"{partition}"
                )

            mode = stat.S_IMODE(
                deployed.stat().st_mode
            )

            if mode != 0o600:
                raise RuntimeError(
                    "deployed AVB private key does not "
                    "have mode 0600: "
                    f"{deployed}"
                )

        results.append(
            AvbBringupKey(
                partition=partition,
                persistent_path=persistent,
                deployed_path=deployed,
                public_key_sha256=(
                    fingerprint
                ),
                generated=generated,
            )
        )

    return (
        AvbBringupKeyProvisioningResult(
            repository_root=repository_root,
            aosp_root=aosp_root,
            device=device,
            keys=tuple(
                results
            ),
        )
    )


def provision_avb_development_keys(
    *,
    repository_root: Path,
    device: str,
    profile: str,
    requirements: tuple[
        tuple[str, str],
        ...,
    ],
) -> tuple[AvbBringupKey, ...]:
    """
    Provision/reuse independent TreeForge AVB development keys.

    The versioned signing profile owns which partitions require independent
    keys and which algorithms they use.

    A public continuity manifest prevents silent trust-identity rotation:
    if a previously recorded key disappears or changes identity, provisioning
    fails instead of silently generating a replacement.
    """

    repository_root = (
        repository_root
        .expanduser()
        .resolve()
    )

    device = device.strip()
    profile = profile.strip()

    if not device:
        raise ValueError(
            "device must not be empty"
        )

    if not profile:
        raise ValueError(
            "profile must not be empty"
        )

    if not requirements:
        raise ValueError(
            "AVB signing requirements "
            "must not be empty"
        )

    normalized: dict[
        str,
        tuple[str, int],
    ] = {}

    for (
        raw_partition,
        raw_algorithm,
    ) in requirements:
        partition = (
            raw_partition.strip()
        )

        algorithm = (
            raw_algorithm.strip()
        )

        if (
            not partition
            or not all(
                character.isalnum()
                or character == "_"
                for character
                in partition
            )
        ):
            raise ValueError(
                "invalid AVB signing "
                f"partition: {partition!r}"
            )

        marker = "_RSA"

        if marker not in algorithm:
            raise ValueError(
                "unsupported AVB signing "
                f"algorithm: {algorithm!r}"
            )

        try:
            bits = int(
                algorithm.rsplit(
                    marker,
                    1,
                )[1],
                10,
            )

        except ValueError as exc:
            raise ValueError(
                "unable to derive RSA "
                "size from AVB algorithm: "
                f"{algorithm!r}"
            ) from exc

        if bits < 2048:
            raise ValueError(
                "TreeForge refuses AVB "
                "RSA keys smaller than "
                "2048 bits"
            )

        current = (
            algorithm,
            bits,
        )

        previous = (
            normalized.get(
                partition
            )
        )

        if (
            previous is not None
            and previous != current
        ):
            raise ValueError(
                "conflicting AVB signing "
                "requirements for "
                f"{partition!r}"
            )

        normalized[
            partition
        ] = current

    openssl = _openssl()

    persistent_root = (
        repository_root
        / ".treeforge-private"
        / "keys"
        / "avb"
        / profile
        / device
    )

    persistent_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    persistent_root.chmod(
        0o700
    )

    manifest_path = (
        persistent_root
        / "key-manifest.json"
    )

    manifest: dict = {
        "schema_version": 1,
        "profile": profile,
        "device": device,
        "keys": {},
    }

    manifest_preexisted = (
        manifest_path.is_file()
    )

    if manifest_preexisted:
        try:
            loaded = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise RuntimeError(
                "TreeForge AVB key "
                "continuity manifest is "
                "unreadable: "
                f"{manifest_path}"
            ) from exc

        if (
            not isinstance(
                loaded,
                dict,
            )
            or loaded.get(
                "schema_version"
            ) != 1
            or loaded.get(
                "profile"
            ) != profile
            or loaded.get(
                "device"
            ) != device
            or not isinstance(
                loaded.get("keys"),
                dict,
            )
        ):
            raise RuntimeError(
                "TreeForge AVB key "
                "continuity manifest has "
                "an invalid identity or "
                "schema: "
                f"{manifest_path}"
            )

        manifest = loaded

    manifest_keys: dict = (
        manifest["keys"]
    )

    realized = []

    for partition in sorted(
        normalized
    ):
        (
            algorithm,
            bits,
        ) = normalized[
            partition
        ]

        path = (
            persistent_root
            / f"{partition}.pem"
        )

        recorded = (
            manifest_keys.get(
                partition
            )
        )

        if (
            recorded is not None
            and not isinstance(
                recorded,
                dict,
            )
        ):
            raise RuntimeError(
                "invalid continuity entry "
                f"for {partition!r}"
            )

        if (
            recorded is not None
            and recorded.get(
                "algorithm"
            ) != algorithm
        ):
            raise RuntimeError(
                "AVB signing algorithm "
                "changed under an existing "
                "key continuity identity: "
                f"{partition}; "
                f"recorded="
                f"{recorded.get('algorithm')!r}, "
                f"requested={algorithm!r}"
            )

        if path.is_symlink():
            raise RuntimeError(
                "TreeForge AVB private "
                "key must not be a "
                f"symlink: {path}"
            )

        generated = False

        if not path.exists():
            if recorded is not None:
                raise RuntimeError(
                    "TreeForge AVB key "
                    "continuity violation: "
                    "previously recorded "
                    "private key is missing; "
                    "refusing silent key "
                    "rotation: "
                    f"{path}"
                )

            subprocess.run(
                [
                    openssl,
                    "genpkey",
                    "-algorithm",
                    "RSA",
                    "-pkeyopt",
                    (
                        "rsa_keygen_bits:"
                        f"{bits}"
                    ),
                    "-out",
                    str(path),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            generated = True

        if not path.is_file():
            raise RuntimeError(
                "TreeForge AVB private "
                "key path is not a "
                "regular file: "
                f"{path}"
            )

        path.chmod(
            0o600
        )

        _validate_rsa_bits(
            openssl=openssl,
            path=path,
            bits=bits,
        )

        fingerprint = (
            _public_fingerprint(
                openssl=openssl,
                path=path,
            )
        )

        if (
            recorded is not None
            and recorded.get(
                "public_key_sha256"
            )
            != fingerprint
        ):
            raise RuntimeError(
                "TreeForge AVB key "
                "continuity violation: "
                "public identity changed "
                f"for {partition!r}; "
                "refusing silent key "
                "rotation"
            )

        manifest_keys[
            partition
        ] = {
            "algorithm": algorithm,
            "public_key_sha256": (
                fingerprint
            ),
        }

        realized.append(
            AvbBringupKey(
                partition=partition,
                persistent_path=path,
                deployed_path=None,
                public_key_sha256=(
                    fingerprint
                ),
                generated=generated,
            )
        )

    temporary_manifest = (
        manifest_path.with_suffix(
            ".json.tmp"
        )
    )

    temporary_manifest.write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    temporary_manifest.chmod(
        0o600
    )

    temporary_manifest.replace(
        manifest_path
    )

    manifest_path.chmod(
        0o600
    )

    return tuple(
        realized
    )



def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Provision/reuse explicit TreeForge "
            "AVB bring-up keys."
        )
    )

    parser.add_argument(
        "--repository-root",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--aosp-root",
        type=Path,
        default=None,
    )

    parser.add_argument(
        "--device",
        default="tangorpro",
    )

    args = parser.parse_args()

    result = (
        provision_avb_bringup_keys(
            repository_root=(
                args.repository_root
            ),
            aosp_root=args.aosp_root,
            device=args.device,
        )
    )

    print(
        "TreeForge AVB bring-up signing inputs"
    )
    print()

    print(
        "These are TreeForge bring-up keys; "
        "they are not OEM/factory private keys."
    )

    print(
        "AOSP test keys selected: NO"
    )

    print(
        "Private material in output/device-tree: NO"
    )

    print()

    for key in result.keys:
        state = (
            "generated"
            if key.generated
            else "reused"
        )

        print(
            f"{key.partition}: {state}"
        )

        print(
            "  RSA bits: 4096"
        )

        print(
            "  public SHA-256: "
            f"{key.public_key_sha256}"
        )

        print(
            "  persistent: "
            f"{key.persistent_path}"
        )

        if key.deployed_path is None:
            print(
                "  AOSP deployment: skipped "
                "(device tree not deployed yet)"
            )

        else:
            print(
                "  AOSP deployment: "
                f"{key.deployed_path}"
            )

    print()

    print(
        "PASS: TreeForge external AVB "
        "bring-up signing inputs are ready"
    )


if __name__ == "__main__":
    main()
