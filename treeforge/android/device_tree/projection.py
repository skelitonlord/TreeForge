from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.reconstruction.source_content.model import (
    AndroidReconstructionSourceContent,
    AndroidReconstructionSourceContentMediaKind,
    AndroidReconstructionSourceContentStatus,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeSourceProjection:
    """
    One deterministic Reconstruction-content -> Device Tree projection.

    ``android_path`` is preserved as runtime/install-path evidence. It is not
    treated as the original Android source-tree location.

    ``destination`` is the generated source-tree path relative to the Device
    Tree workspace root.
    """

    content_id: str
    representation_id: str
    family: str

    destination: PurePosixPath

    android_path: PurePosixPath | None
    source_path: Path

    content: AndroidReconstructionSourceContent

    def __post_init__(self) -> None:
        for field_name, value in (
            ("content_id", self.content_id),
            ("representation_id", self.representation_id),
            ("family", self.family),
        ):
            if not isinstance(value, str) or not value:
                raise ValueError(
                    f"{field_name} must be a non-empty string"
                )

        if not isinstance(
            self.destination,
            PurePosixPath,
        ):
            raise TypeError(
                "destination must be a PurePosixPath"
            )

        if self.destination.is_absolute():
            raise ValueError(
                "destination must be relative to the "
                "Device Tree workspace"
            )

        if ".." in self.destination.parts:
            raise ValueError(
                "destination must not escape the "
                "Device Tree workspace"
            )

        if (
            self.android_path is not None
            and not isinstance(
                self.android_path,
                PurePosixPath,
            )
        ):
            raise TypeError(
                "android_path must be a PurePosixPath or None"
            )

        if not isinstance(
            self.source_path,
            Path,
        ):
            raise TypeError(
                "source_path must be a Path"
            )

        if not isinstance(
            self.content,
            AndroidReconstructionSourceContent,
        ):
            raise TypeError(
                "content must be an "
                "AndroidReconstructionSourceContent"
            )

        if self.content.content_id != self.content_id:
            raise ValueError(
                "projection content_id must preserve "
                "Reconstruction content identity"
            )

        if (
            self.content.representation_id
            != self.representation_id
        ):
            raise ValueError(
                "projection representation_id must preserve "
                "Reconstruction representation identity"
            )

        has_text = (
            self.content.text is not None
        )
        has_bytes = (
            self.content.raw_bytes is not None
        )

        if has_text == has_bytes:
            raise ValueError(
                "projected Device Tree content must carry "
                "exactly one payload form: text or raw_bytes"
            )


class AndroidDeviceTreeDestinationProjector:
    """
    Project source-content families whose canonical Reconstruction
    representations already preserve enough path identity.

    Supported:
    - INIT
    - fstab
    - ueventd
    - VINTF
    - SELinux exact-byte preservation

    Runtime properties deliberately remain outside this projector because
    Reconstruction currently marks them NOT_SOURCE_DECLARABLE.
    """

    _FAMILY_INIT = "init"
    _FAMILY_FSTAB = "fstab"
    _FAMILY_UEVENTD = "ueventd"
    _FAMILY_VINTF = "vintf"
    _FAMILY_SELINUX = "selinux"

    @classmethod
    def project(
        cls,
        reconstruction: AndroidReconstructionResult,
        *,
        identity: AndroidDeviceTreeIdentity,
    ) -> tuple[
        AndroidDeviceTreeSourceProjection,
        ...,
    ]:
        if not isinstance(
            reconstruction,
            AndroidReconstructionResult,
        ):
            raise TypeError(
                "reconstruction must be an "
                "AndroidReconstructionResult"
            )

        if not isinstance(
            identity,
            AndroidDeviceTreeIdentity,
        ):
            raise TypeError(
                "identity must be an "
                "AndroidDeviceTreeIdentity"
            )

        projections: list[
            AndroidDeviceTreeSourceProjection
        ] = []

        projections.extend(
            cls._project_init(
                representations=(
                    reconstruction
                    .init_source_representations
                ),
                contents=(
                    reconstruction
                    .init_source_contents
                ),
                generated_root=(
                    identity.device_root
                ),
            )
        )

        projections.extend(
            cls._project_family(
                family=cls._FAMILY_FSTAB,
                representations=(
                    reconstruction
                    .fstab_source_representations
                ),
                contents=(
                    reconstruction
                    .fstab_source_contents
                ),
                expected_media_kind=(
                    AndroidReconstructionSourceContentMediaKind
                    .FSTAB
                ),
                generated_root=(
                    identity.device_root
                ),
            )
        )

        projections.extend(
            cls._project_family(
                family=cls._FAMILY_UEVENTD,
                representations=(
                    reconstruction
                    .ueventd_source_representations
                ),
                contents=(
                    reconstruction
                    .ueventd_source_contents
                ),
                expected_media_kind=(
                    AndroidReconstructionSourceContentMediaKind
                    .UEVENTD
                ),
                generated_root=(
                    identity.device_root
                ),
            )
        )

        projections.extend(
            cls._project_family(
                family=cls._FAMILY_VINTF,
                representations=(
                    reconstruction
                    .vintf_document_representations
                ),
                contents=(
                    reconstruction
                    .vintf_source_contents
                ),
                expected_media_kind=(
                    AndroidReconstructionSourceContentMediaKind
                    .VINTF_XML
                ),
                generated_root=(
                    identity.device_root
                ),
            )
        )

        projections.extend(
            cls._project_selinux(
                representations=(
                    reconstruction
                    .selinux_source_representations
                ),
                contents=(
                    reconstruction
                    .selinux_source_contents
                ),
                generated_root=(
                    identity.device_root
                ),
            )
        )

        result = tuple(
            sorted(
                projections,
                key=lambda item: (
                    item.destination.as_posix(),
                    item.content_id,
                ),
            )
        )

        destination_ids = tuple(
            item.destination.as_posix()
            for item in result
        )

        if len(destination_ids) != len(
            set(destination_ids)
        ):
            raise ValueError(
                "Device Tree projections must have "
                "unique destinations"
            )

        content_ids = tuple(
            item.content_id
            for item in result
        )

        if len(content_ids) != len(
            set(content_ids)
        ):
            raise ValueError(
                "Device Tree projections must contain "
                "unique Reconstruction content"
            )

        return result

    @classmethod
    def _project_init(
        cls,
        *,
        representations: tuple[object, ...],
        contents: tuple[
            AndroidReconstructionSourceContent,
            ...,
        ],
        generated_root: Path,
    ) -> tuple[
        AndroidDeviceTreeSourceProjection,
        ...,
    ]:
        """
        Project canonical INIT source groups.

        INIT source identity intentionally contains both parser filesystem
        identity and Android-visible path identity, so the representation
        itself does not expose a standalone source_path/android_path pair.

        Device Tree recovers those exact path identities from the canonical
        Planning obligations retained by the representation. It does not
        reinterpret imports, services, actions, or source applicability.
        """

        representation_by_id = {}

        for representation in representations:
            representation_id = getattr(
                representation,
                "representation_id",
                None,
            )

            if (
                not isinstance(
                    representation_id,
                    str,
                )
                or not representation_id
            ):
                raise ValueError(
                    "INIT representation has no valid "
                    "representation_id"
                )

            if representation_id in representation_by_id:
                raise ValueError(
                    "INIT representation identities "
                    "must be unique"
                )

            representation_by_id[
                representation_id
            ] = representation

        content_by_representation = {}

        for content in contents:
            if not isinstance(
                content,
                AndroidReconstructionSourceContent,
            ):
                raise TypeError(
                    "INIT contents contain an invalid model"
                )

            if (
                content.media_kind
                is not
                AndroidReconstructionSourceContentMediaKind
                .INIT_RC
            ):
                raise ValueError(
                    "INIT content has the wrong media kind"
                )

            if (
                content.representation_id
                in content_by_representation
            ):
                raise ValueError(
                    "INIT must contain exactly one content "
                    "unit per representation"
                )

            content_by_representation[
                content.representation_id
            ] = content

        if (
            set(representation_by_id)
            != set(content_by_representation)
        ):
            missing_content = sorted(
                set(representation_by_id)
                - set(content_by_representation)
            )

            missing_representation = sorted(
                set(content_by_representation)
                - set(representation_by_id)
            )

            raise ValueError(
                "INIT Reconstruction content/representation "
                "coverage mismatch: "
                f"missing_content={missing_content!r}, "
                f"missing_representation="
                f"{missing_representation!r}"
            )

        candidates = []

        for representation_id in sorted(
            representation_by_id
        ):
            representation = (
                representation_by_id[
                    representation_id
                ]
            )

            source_group = getattr(
                representation,
                "source_group",
                None,
            )

            obligations = getattr(
                source_group,
                "obligations",
                None,
            )

            if (
                not isinstance(
                    obligations,
                    tuple,
                )
                or not obligations
            ):
                raise ValueError(
                    "INIT representation must retain a "
                    "non-empty canonical source group"
                )

            requirements = tuple(
                obligation.requirement
                for obligation in obligations
            )

            source_paths = {
                requirement.source_path
                for requirement in requirements
            }

            android_paths = {
                requirement.android_path
                for requirement in requirements
            }

            if len(source_paths) != 1:
                raise ValueError(
                    "INIT source group must preserve exactly "
                    "one physical source_path"
                )

            if len(android_paths) != 1:
                raise ValueError(
                    "INIT source group must preserve exactly "
                    "one Android-visible path"
                )

            source_path = next(
                iter(source_paths)
            )

            android_path = next(
                iter(android_paths)
            )

            if not isinstance(
                source_path,
                Path,
            ):
                raise TypeError(
                    "INIT requirement source_path "
                    "must be a Path"
                )

            if (
                android_path is not None
                and not isinstance(
                    android_path,
                    PurePosixPath,
                )
            ):
                raise TypeError(
                    "INIT requirement android_path must be "
                    "PurePosixPath or None"
                )

            preferred_name = (
                android_path.name
                if (
                    android_path is not None
                    and android_path.name
                )
                else source_path.name
            )

            if not preferred_name:
                raise ValueError(
                    "INIT source has no usable filename"
                )

            if not preferred_name.endswith(
                ".rc"
            ):
                preferred_name = (
                    f"{preferred_name}.rc"
                )

            candidates.append(
                (
                    representation_id,
                    source_path,
                    android_path,
                    preferred_name,
                )
            )

        name_counts: dict[str, int] = {}

        for (
            _,
            _,
            _,
            preferred_name,
        ) in candidates:
            name_counts[preferred_name] = (
                name_counts.get(
                    preferred_name,
                    0,
                )
                + 1
            )

        projected = []

        for (
            representation_id,
            source_path,
            android_path,
            preferred_name,
        ) in candidates:
            filename = preferred_name

            if name_counts[preferred_name] > 1:
                filename = cls._qualified_filename(
                    preferred_name,
                    representation_id,
                )

            content = content_by_representation[
                representation_id
            ]

            destination = PurePosixPath(
                (
                    generated_root
                    / cls._FAMILY_INIT
                    / filename
                ).as_posix()
            )

            projected.append(
                AndroidDeviceTreeSourceProjection(
                    content_id=(
                        content.content_id
                    ),
                    representation_id=(
                        representation_id
                    ),
                    family=cls._FAMILY_INIT,
                    destination=destination,
                    android_path=android_path,
                    source_path=source_path,
                    content=content,
                )
            )

        return tuple(projected)

    @classmethod
    def _project_selinux(
        cls,
        *,
        representations: tuple[object, ...],
        contents: tuple[
            AndroidReconstructionSourceContent,
            ...,
        ],
        generated_root: Path,
    ) -> tuple[
        AndroidDeviceTreeSourceProjection,
        ...,
    ]:
        """
        Preserve exact SELinux source bytes.

        Textual policy is placed under ``sepolicy/source``.
        Opaque/compiled policy is retained separately under
        ``sepolicy/opaque`` and is never represented as reconstructed
        textual source.
        """

        representation_by_id = {}

        for representation in representations:
            representation_id = getattr(
                representation,
                "representation_id",
                None,
            )

            if (
                not isinstance(
                    representation_id,
                    str,
                )
                or not representation_id
            ):
                raise ValueError(
                    "SELinux representation has no valid "
                    "representation_id"
                )

            if representation_id in representation_by_id:
                raise ValueError(
                    "SELinux representation identities "
                    "must be unique"
                )

            representation_by_id[
                representation_id
            ] = representation

        content_by_representation = {}

        for content in contents:
            if not isinstance(
                content,
                AndroidReconstructionSourceContent,
            ):
                raise TypeError(
                    "SELinux contents contain an invalid model"
                )

            if (
                content.media_kind
                is not
                AndroidReconstructionSourceContentMediaKind
                .SELINUX
            ):
                raise ValueError(
                    "SELinux content has the wrong media kind"
                )

            if content.raw_bytes is None:
                raise ValueError(
                    "SELinux content must preserve exact raw bytes"
                )

            if content.text is not None:
                raise ValueError(
                    "SELinux exact-byte content must not also "
                    "carry regenerated text"
                )

            if (
                content.status
                not in (
                    AndroidReconstructionSourceContentStatus
                    .PRESERVED_EXACT,
                    AndroidReconstructionSourceContentStatus
                    .OPAQUE,
                )
            ):
                raise ValueError(
                    "SELinux content must be PRESERVED_EXACT "
                    "or OPAQUE"
                )

            if (
                content.representation_id
                in content_by_representation
            ):
                raise ValueError(
                    "SELinux must contain exactly one content "
                    "unit per representation"
                )

            content_by_representation[
                content.representation_id
            ] = content

        if (
            set(representation_by_id)
            != set(content_by_representation)
        ):
            raise ValueError(
                "SELinux Reconstruction content/representation "
                "coverage mismatch"
            )

        candidates = []

        for representation_id in sorted(
            representation_by_id
        ):
            representation = (
                representation_by_id[
                    representation_id
                ]
            )

            source_path = getattr(
                representation,
                "source_path",
                None,
            )
            android_path = getattr(
                representation,
                "android_path",
                None,
            )

            if not isinstance(
                source_path,
                Path,
            ):
                raise TypeError(
                    "SELinux representation must preserve source_path"
                )

            if (
                android_path is not None
                and not isinstance(
                    android_path,
                    PurePosixPath,
                )
            ):
                raise TypeError(
                    "SELinux representation android_path must be "
                    "PurePosixPath or None"
                )

            preferred_name = (
                android_path.name
                if (
                    android_path is not None
                    and android_path.name
                )
                else source_path.name
            )

            if not preferred_name:
                raise ValueError(
                    "SELinux representation has no usable filename"
                )

            content = content_by_representation[
                representation_id
            ]

            source_kind = getattr(
                representation,
                "source_kind",
                None,
            )

            source_kind_value = getattr(
                source_kind,
                "value",
                None,
            )

            generic_vendor_source_names = {
                "file_contexts": "file_contexts",
                "property_contexts": "property_contexts",
                "service_contexts": "service_contexts",
                "hwservice_contexts": "hwservice_contexts",
                "vndservice_contexts": "vndservice_contexts",
                "keystore2_key_contexts": "keystore2_key_contexts",
            }

            generic_source_name = None

            if (
                android_path is not None
                and android_path.as_posix().startswith(
                    "/vendor/etc/selinux/"
                )
            ):
                generic_source_name = (
                    generic_vendor_source_names.get(
                        source_kind_value
                    )
                )

                if (
                    generic_source_name is None
                    and source_kind_value == "other_text"
                    and android_path.name
                    == "selinux_denial_metadata"
                ):
                    generic_source_name = "bug_map"

            if generic_source_name is not None:
                preferred_name = generic_source_name
                bucket = "vendor"
            else:
                bucket = (
                    "opaque"
                    if (
                        content.status
                        is AndroidReconstructionSourceContentStatus
                        .OPAQUE
                    )
                    else "source"
                )

            candidates.append(
                (
                    representation_id,
                    source_path,
                    android_path,
                    preferred_name,
                    bucket,
                    content,
                )
            )

        counts: dict[
            tuple[str, str],
            int,
        ] = {}

        for (
            _,
            _,
            _,
            preferred_name,
            bucket,
            _,
        ) in candidates:
            key = (
                bucket,
                preferred_name,
            )

            counts[key] = (
                counts.get(
                    key,
                    0,
                )
                + 1
            )

        projected = []

        for (
            representation_id,
            source_path,
            android_path,
            preferred_name,
            bucket,
            content,
        ) in candidates:
            filename = preferred_name

            if (
                counts[
                    (
                        bucket,
                        preferred_name,
                    )
                ]
                > 1
            ):
                filename = cls._qualified_filename(
                    preferred_name,
                    representation_id,
                )

            destination = PurePosixPath(
                (
                    generated_root
                    / "sepolicy"
                    / bucket
                    / filename
                ).as_posix()
            )

            projected.append(
                AndroidDeviceTreeSourceProjection(
                    content_id=content.content_id,
                    representation_id=representation_id,
                    family=cls._FAMILY_SELINUX,
                    destination=destination,
                    android_path=android_path,
                    source_path=source_path,
                    content=content,
                )
            )

        return tuple(projected)

    @classmethod
    def _project_family(
        cls,
        *,
        family: str,
        representations: tuple[object, ...],
        contents: tuple[
            AndroidReconstructionSourceContent,
            ...,
        ],
        expected_media_kind: (
            AndroidReconstructionSourceContentMediaKind
        ),
        generated_root: Path,
    ) -> tuple[
        AndroidDeviceTreeSourceProjection,
        ...,
    ]:
        representation_by_id = {}

        for representation in representations:
            representation_id = getattr(
                representation,
                "representation_id",
                None,
            )

            if (
                not isinstance(
                    representation_id,
                    str,
                )
                or not representation_id
            ):
                raise ValueError(
                    f"{family} representation has no "
                    "valid representation_id"
                )

            if representation_id in representation_by_id:
                raise ValueError(
                    f"{family} representation identities "
                    "must be unique"
                )

            representation_by_id[
                representation_id
            ] = representation

        content_by_representation = {}

        for content in contents:
            if not isinstance(
                content,
                AndroidReconstructionSourceContent,
            ):
                raise TypeError(
                    f"{family} contents contain an "
                    "invalid model"
                )

            if (
                content.media_kind
                is not expected_media_kind
            ):
                raise ValueError(
                    f"{family} content has the wrong "
                    "media kind"
                )

            if (
                content.representation_id
                in content_by_representation
            ):
                raise ValueError(
                    f"{family} must contain exactly one "
                    "content unit per representation"
                )

            content_by_representation[
                content.representation_id
            ] = content

        if (
            set(representation_by_id)
            != set(content_by_representation)
        ):
            missing_content = sorted(
                set(representation_by_id)
                - set(content_by_representation)
            )

            missing_representation = sorted(
                set(content_by_representation)
                - set(representation_by_id)
            )

            raise ValueError(
                f"{family} Reconstruction content/representation "
                "coverage mismatch: "
                f"missing_content={missing_content!r}, "
                f"missing_representation="
                f"{missing_representation!r}"
            )

        candidates = []

        for representation_id in sorted(
            representation_by_id
        ):
            representation = (
                representation_by_id[
                    representation_id
                ]
            )

            source_path = getattr(
                representation,
                "source_path",
                None,
            )

            android_path = getattr(
                representation,
                "android_path",
                None,
            )

            if not isinstance(
                source_path,
                Path,
            ):
                raise TypeError(
                    f"{family} representation must "
                    "preserve source_path"
                )

            if (
                android_path is not None
                and not isinstance(
                    android_path,
                    PurePosixPath,
                )
            ):
                raise TypeError(
                    f"{family} representation android_path "
                    "must be PurePosixPath or None"
                )

            preferred_name = (
                android_path.name
                if (
                    android_path is not None
                    and android_path.name
                )
                else source_path.name
            )

            if not preferred_name:
                raise ValueError(
                    f"{family} representation has no "
                    "usable source filename"
                )

            candidates.append(
                (
                    representation_id,
                    representation,
                    preferred_name,
                )
            )

        name_counts: dict[str, int] = {}

        for _, _, preferred_name in candidates:
            name_counts[preferred_name] = (
                name_counts.get(
                    preferred_name,
                    0,
                )
                + 1
            )

        projected = []

        for (
            representation_id,
            representation,
            preferred_name,
        ) in candidates:
            filename = preferred_name

            if name_counts[preferred_name] > 1:
                filename = cls._qualified_filename(
                    preferred_name,
                    representation_id,
                )

            destination = PurePosixPath(
                (
                    generated_root
                    / family
                    / filename
                ).as_posix()
            )

            content = content_by_representation[
                representation_id
            ]

            projected.append(
                AndroidDeviceTreeSourceProjection(
                    content_id=(
                        content.content_id
                    ),
                    representation_id=(
                        representation_id
                    ),
                    family=family,
                    destination=destination,
                    android_path=getattr(
                        representation,
                        "android_path",
                    ),
                    source_path=getattr(
                        representation,
                        "source_path",
                    ),
                    content=content,
                )
            )

        return tuple(projected)

    @staticmethod
    def _qualified_filename(
        filename: str,
        representation_id: str,
    ) -> str:
        digest = sha256(
            representation_id.encode(
                "utf-8"
            )
        ).hexdigest()[:12]

        path = PurePosixPath(filename)

        suffixes = "".join(
            path.suffixes
        )

        if suffixes:
            stem = filename[
                :-len(suffixes)
            ]
            return (
                f"{stem}-{digest}"
                f"{suffixes}"
            )

        return f"{filename}-{digest}"
