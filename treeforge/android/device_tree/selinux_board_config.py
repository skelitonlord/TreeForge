from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from treeforge.android.device_tree.selinux_derived_source import (
    AndroidDeviceTreeDerivedSelinuxSource,
)

from treeforge.android.device_tree.build_realization import (
    AndroidDeviceTreeBuildRealization,
    AndroidDeviceTreeBuildRealizationKind,
    AndroidDeviceTreeBuildRealizationStatus,
)
from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.reconstruction.model import (
    AndroidReconstructionResult,
)
from treeforge.android.reconstruction.build_system.model import (
    AndroidReconstructionBuildRepresentationKind,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeSelinuxBoardConfig:
    vendor_policy_dirs: tuple[PurePosixPath, ...] = ()
    odm_policy_dirs: tuple[PurePosixPath, ...] = ()
    product_public_policy_dirs: tuple[
        PurePosixPath,
        ...,
    ] = ()
    product_private_policy_dirs: tuple[
        PurePosixPath,
        ...,
    ] = ()
    system_ext_public_policy_dirs: tuple[
        PurePosixPath,
        ...,
    ] = ()
    system_ext_private_policy_dirs: tuple[
        PurePosixPath,
        ...,
    ] = ()


class AndroidDeviceTreeSelinuxBoardConfigRenderer:
    """
    Render only proven source-equivalent SELinux policy directories.

    Runtime SELinux artifacts that remain PARTIAL are never admitted into
    Android policy source-directory variables.
    """

    _VARIABLE_BY_RELATIVE_ROOT = {
        ("vendor",): "BOARD_VENDOR_SEPOLICY_DIRS",
        ("odm",): "BOARD_ODM_SEPOLICY_DIRS",
        (
            "product",
            "public",
        ): "PRODUCT_PUBLIC_SEPOLICY_DIRS",
        (
            "product",
            "private",
        ): "PRODUCT_PRIVATE_SEPOLICY_DIRS",
        (
            "system_ext",
            "public",
        ): "SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS",
        (
            "system_ext",
            "private",
        ): "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS",
    }

    @classmethod
    def project(
        cls,
        *,
        reconstruction: AndroidReconstructionResult,
        identity: AndroidDeviceTreeIdentity,
        realizations: tuple[
            AndroidDeviceTreeBuildRealization,
            ...,
        ],
        derived_sources: tuple[
            AndroidDeviceTreeDerivedSelinuxSource,
            ...,
        ],
    ) -> AndroidDeviceTreeSelinuxBoardConfig:
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
                "identity must be an AndroidDeviceTreeIdentity"
            )

        if not isinstance(
            realizations,
            tuple,
        ):
            raise TypeError(
                "realizations must be a tuple"
            )

        if not isinstance(
            derived_sources,
            tuple,
        ):
            raise TypeError(
                "derived_sources must be a tuple"
            )

        if not all(
            isinstance(
                source,
                AndroidDeviceTreeDerivedSelinuxSource,
            )
            for source in derived_sources
        ):
            raise TypeError(
                "derived_sources must contain only "
                "AndroidDeviceTreeDerivedSelinuxSource values"
            )

        sepolicy_root = (
            PurePosixPath(
                identity.device_root.as_posix()
            )
            / "sepolicy"
        )

        expected_roots = {
            relative_parts: (
                sepolicy_root.joinpath(
                    *relative_parts
                )
            )
            for relative_parts
            in cls._VARIABLE_BY_RELATIVE_ROOT
        }

        dirs_by_variable = {
            variable: set()
            for variable
            in cls._VARIABLE_BY_RELATIVE_ROOT.values()
        }

        # Device Tree preserves exactly one build realization for each
        # Reconstruction build representation, while each generated SELinux
        # source retains the identity of its Reconstruction SELinux source
        # representation.
        #
        # These are intentionally different identity domains. Bridge them
        # through the exact Reconstruction source-content identity:
        #
        #   SELinux source representation
        #       -> SELinux source content
        #       -> build representation.source_content_id
        #       -> resolved Device Tree SELINUX_POLICY realization
        #
        # Never compare source_representation_id directly with a Device Tree
        # build realization's representation_id.

        content_by_source_representation_id = {
            content.representation_id:
            content
            for content
            in reconstruction.selinux_source_contents
        }

        if len(
            content_by_source_representation_id
        ) != len(
            reconstruction.selinux_source_contents
        ):
            raise ValueError(
                "Reconstruction SELinux source contents must preserve "
                "unique source representation identity"
            )

        resolved_policy_content_ids = set()

        for realization in realizations:
            if (
                realization.status
                is not AndroidDeviceTreeBuildRealizationStatus
                .RESOLVED
            ):
                continue

            if (
                realization.kind
                is not AndroidDeviceTreeBuildRealizationKind
                .SELINUX_POLICY
            ):
                continue

            representation = (
                realization.build_representation
            )

            if (
                representation.kind
                is not AndroidReconstructionBuildRepresentationKind
                .SELINUX_RUNTIME_OUTPUT
            ):
                continue

            if realization.source_path is None:
                raise ValueError(
                    "resolved source-equivalent SELinux realization "
                    "requires a source_path"
                )

            source_content_id = (
                representation.source_content_id
            )

            if source_content_id is None:
                raise ValueError(
                    "resolved source-equivalent SELinux realization "
                    "requires canonical source_content_id"
                )

            resolved_policy_content_ids.add(
                source_content_id
            )

        for source in derived_sources:
            source_content = (
                content_by_source_representation_id.get(
                    source.source_representation_id
                )
            )

            if source_content is None:
                raise ValueError(
                    "derived SELinux source has no matching "
                    "Reconstruction SELinux source content: "
                    f"{source.source_representation_id}"
                )

            if (
                source_content.content_id
                not in resolved_policy_content_ids
            ):
                # Exact canonical source population has not been promoted
                # to a resolved source-equivalent Device Tree policy.
                continue

            destination = source.destination

            matching_roots = tuple(
                (
                    relative_parts,
                    expected_root,
                )
                for (
                    relative_parts,
                    expected_root,
                ) in expected_roots.items()
                if destination.is_relative_to(
                    expected_root
                )
            )

            if not matching_roots:
                raise ValueError(
                    "resolved source-equivalent SELinux input "
                    "does not live in a canonical Android policy "
                    "source directory: "
                    f"{destination.as_posix()}"
                )

            if len(matching_roots) != 1:
                raise ValueError(
                    "resolved source-equivalent SELinux input "
                    "matches multiple canonical Android policy "
                    "source directories: "
                    f"{destination.as_posix()}"
                )

            (
                relative_parts,
                source_root,
            ) = matching_roots[0]

            variable = (
                cls._VARIABLE_BY_RELATIVE_ROOT[
                    relative_parts
                ]
            )

            dirs_by_variable[
                variable
            ].add(
                source_root
            )

        def ordered(variable):
            return tuple(
                sorted(
                    dirs_by_variable[variable],
                    key=lambda value: (
                        value.as_posix()
                    ),
                )
            )

        return AndroidDeviceTreeSelinuxBoardConfig(
            vendor_policy_dirs=ordered(
                "BOARD_VENDOR_SEPOLICY_DIRS"
            ),
            odm_policy_dirs=ordered(
                "BOARD_ODM_SEPOLICY_DIRS"
            ),
            product_public_policy_dirs=ordered(
                "PRODUCT_PUBLIC_SEPOLICY_DIRS"
            ),
            product_private_policy_dirs=ordered(
                "PRODUCT_PRIVATE_SEPOLICY_DIRS"
            ),
            system_ext_public_policy_dirs=ordered(
                "SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS"
            ),
            system_ext_private_policy_dirs=ordered(
                "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS"
            ),
        )

    @staticmethod
    def _render_variable(
        variable: str,
        values: tuple[
            PurePosixPath,
            ...,
        ],
    ) -> list[str]:
        if not values:
            return []

        lines = [
            f"{variable} += \\",
        ]

        for index, value in enumerate(values):
            suffix = (
                " \\"
                if index < len(values) - 1
                else ""
            )

            lines.append(
                f"    {value.as_posix()}{suffix}"
            )

        lines.append("")

        return lines

    @classmethod
    def render(
        cls,
        config: AndroidDeviceTreeSelinuxBoardConfig,
    ) -> str:
        if not isinstance(
            config,
            AndroidDeviceTreeSelinuxBoardConfig,
        ):
            raise TypeError(
                "config must be an "
                "AndroidDeviceTreeSelinuxBoardConfig"
            )

        groups = (
            (
                "BOARD_VENDOR_SEPOLICY_DIRS",
                config.vendor_policy_dirs,
            ),
            (
                "BOARD_ODM_SEPOLICY_DIRS",
                config.odm_policy_dirs,
            ),
            (
                "PRODUCT_PUBLIC_SEPOLICY_DIRS",
                config.product_public_policy_dirs,
            ),
            (
                "PRODUCT_PRIVATE_SEPOLICY_DIRS",
                config.product_private_policy_dirs,
            ),
            (
                "SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS",
                config.system_ext_public_policy_dirs,
            ),
            (
                "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS",
                config.system_ext_private_policy_dirs,
            ),
        )

        if not any(
            values
            for _, values in groups
        ):
            return ""

        lines = [
            "# Generic source-equivalent SELinux integration.",
            "",
        ]

        for variable, values in groups:
            lines.extend(
                cls._render_variable(
                    variable,
                    values,
                )
            )

        return "\n".join(lines)
