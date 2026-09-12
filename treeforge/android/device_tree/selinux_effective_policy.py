from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import PurePosixPath

from treeforge.android.device_tree.model import (
    AndroidDeviceTreeIdentity,
)
from treeforge.android.device_tree.selinux_derived_source import (
    AndroidDeviceTreeDerivedSelinuxSource,
)
from treeforge.android.parsing.selinux import (
    AndroidSelinuxCilAtom,
    AndroidSelinuxCilExpression,
    AndroidSelinuxCilList,
)


@dataclass(frozen=True, slots=True)
class AndroidDeviceTreeEffectiveSelinuxSynthesis:
    """
    Conservative Device Tree synthesis of vendor SELinux source policy.

    ``rendered_form_names`` are CIL families for which this renderer emitted
    Android source-policy syntax.

    ``generated_form_names`` are CIL bookkeeping forms known to arise from
    source-policy compilation/versioning and which therefore do not require
    an independent source statement here.

    ``unsupported_form_names`` remain explicit blockers to treating the
    synthesized source as semantically complete.
    """

    sources: tuple[
        AndroidDeviceTreeDerivedSelinuxSource,
        ...,
    ] = ()

    rendered_form_names: tuple[str, ...] = ()
    generated_form_names: tuple[str, ...] = ()
    unsupported_form_names: tuple[str, ...] = ()

    rendered_requirement_count: int = 0
    generated_requirement_count: int = 0
    unsupported_requirement_count: int = 0

    @property
    def complete(self) -> bool:
        return (
            bool(self.sources)
            and self.unsupported_requirement_count == 0
        )


class AndroidDeviceTreeEffectiveSelinuxRenderer:
    """
    Synthesize deterministic Android partition policy source from canonical
    factory-derived CIL semantics.

    This renderer does not reproduce the OEM's original macros or file
    organization. It reconstructs only source-policy statements whose
    semantics can be recovered without unsupported inference.

    The effective factory policy has already passed through Android policy
    versioning. Versioned platform-public symbols are mapped back only when:
      1. the platform policy version is canonically observed, and
      2. that exact suffixed symbol occurs in plat_pub_versioned.cil.

    No suffix is stripped merely because it looks version-like.
    """

    _CIL_PATH_BY_PARTITION = {
        "vendor": PurePosixPath(
            "/vendor/etc/selinux/vendor_sepolicy.cil"
        ),
        "system_ext": PurePosixPath(
            "/system_ext/etc/selinux/system_ext_sepolicy.cil"
        ),
        "product": PurePosixPath(
            "/product/etc/selinux/product_sepolicy.cil"
        ),
    }

    _PLAT_PUB_VERSIONED_PATH = PurePosixPath(
        "/vendor/etc/selinux/plat_pub_versioned.cil"
    )

    _PLAT_VERSION_PATH = PurePosixPath(
        "/vendor/etc/selinux/plat_sepolicy_vers.txt"
    )

    # These forms must not be reconstructed as independent target
    # Android source-policy statements.
    #
    # roletype / expandtypeattribute are CIL/compiler bookkeeping.
    #
    # neverallow is also intentionally retained only as observed provenance:
    # it is a source-build assertion, not runtime access policy.  Factory CIL
    # contains the already-expanded result of source conditionals such as
    # build-variant selection.  Replaying that assertion into a different
    # target AOSP build can therefore impose constraints that were never
    # active for the target configuration.
    _GENERATED_FORMS = {
        "roletype",
        "expandtypeattribute",
        "neverallow",
    }

    _RENDERED_DECLARATIONS = {
        "type",
        "typeattribute",
    }

    _RENDERED_ACCESS = {
        "allow",
        "auditallow",
        "dontaudit",
    }

    @classmethod
    def project(
        cls,
        reconstruction,
        *,
        identity: AndroidDeviceTreeIdentity,
        partition: str = "vendor",
    ) -> AndroidDeviceTreeEffectiveSelinuxSynthesis:
        from treeforge.android.reconstruction.model import (
            AndroidReconstructionResult,
        )

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

        if not isinstance(partition, str):
            raise TypeError(
                "partition must be a string"
            )

        if partition not in cls._CIL_PATH_BY_PARTITION:
            raise ValueError(
                "unsupported effective SELinux partition: "
                f"{partition!r}"
            )

        policy_path = (
            cls._CIL_PATH_BY_PARTITION[
                partition
            ]
        )

        universe = (
            reconstruction
            .reconstruction_input
            .runtime_linking
            .universe
        )

        policy_representation = cls._representation_for_path(
            reconstruction,
            policy_path,
        )

        if policy_representation is None:
            return AndroidDeviceTreeEffectiveSelinuxSynthesis()

        policy_requirement = policy_representation.requirement

        if not policy_requirement.cil_requirements:
            return AndroidDeviceTreeEffectiveSelinuxSynthesis(
                unsupported_form_names=(
                    (
                        f"<{partition}-cil-without-"
                        "canonical-forms>"
                    ),
                ),
                unsupported_requirement_count=1,
            )

        version_requirement = cls._universe_requirement_for_path(
            universe,
            cls._PLAT_VERSION_PATH,
        )

        public_requirement = cls._universe_requirement_for_path(
            universe,
            cls._PLAT_PUB_VERSIONED_PATH,
        )

        policy_version = None

        if version_requirement is not None:
            parsed = version_requirement.parsed

            text_lines = getattr(
                parsed,
                "text_lines",
                (),
            )

            candidates = []

            for line in text_lines:
                value = getattr(
                    line,
                    "content",
                    None,
                )

                if value is None:
                    value = getattr(
                        line,
                        "raw",
                        None,
                    )

                if isinstance(value, str):
                    value = value.strip()

                    if value:
                        candidates.append(value)

            if not candidates:
                raw_text = getattr(
                    parsed,
                    "raw_text",
                    None,
                )

                if isinstance(raw_text, str):
                    candidates.extend(
                        value.strip()
                        for value in raw_text.splitlines()
                        if value.strip()
                    )

            if len(set(candidates)) == 1:
                policy_version = candidates[0]

        # Some parser models expose this value directly.
        if (
            policy_version is None
            and version_requirement is not None
        ):
            candidate = getattr(
                version_requirement.parsed,
                "policy_version",
                None,
            )

            if isinstance(candidate, str) and candidate:
                policy_version = candidate

        versioned_public_symbols = set()

        if (
            public_requirement is not None
            and policy_version is not None
        ):
            suffix = f"_{policy_version}"

            for requirement in public_requirement.cil_requirements:
                for atom in cls._atoms(
                    requirement.form.expression
                ):
                    if atom.endswith(suffix):
                        versioned_public_symbols.add(atom)

        def normalize_symbol(value: str) -> str:
            if (
                policy_version is None
                or value not in versioned_public_symbols
            ):
                return value

            suffix = f"_{policy_version}"

            if not value.endswith(suffix):
                return value

            normalized = value[:-len(suffix)]

            return normalized or value

        complex_type_sets = {}

        # Compiler-generated type-set temporaries referenced by effective CIL
        # are not necessarily declared inside vendor_sepolicy.cil itself.
        # Android's compiled vendor policy participates in the combined
        # platform/vendor policy namespace, so resolve those temporary-set
        # definitions from the complete canonical SELinux CIL universe.
        #
        # This does not move ownership backward or copy platform policy into
        # the vendor source tree: only the temporary expression definition
        # is consumed so a partition-owned rule can be reconstructed back into
        # source-level TE set syntax.
        for source_requirement in universe.selinux_requirements:
            for requirement in source_requirement.cil_requirements:
                if requirement.form_name != "typeattributeset":
                    continue

                rendered_set = (
                    cls._render_complex_type_attribute_set(
                        requirement,
                        normalize_symbol=normalize_symbol,
                    )
                )

                if rendered_set is None:
                    continue

                attribute, expression = rendered_set

                # base_typeattr_* is the compiler-generated namespace proven
                # by the canonical CIL evidence. Do not reinterpret arbitrary
                # source-owned type attributes as temporary set expressions.
                if not attribute.startswith("base_typeattr_"):
                    continue

                existing = complex_type_sets.get(
                    attribute
                )

                if (
                    existing is not None
                    and existing != expression
                ):
                    raise ValueError(
                        "conflicting canonical SELinux complex "
                        "type-set definitions for "
                        f"{attribute!r}: "
                        f"{existing!r} != {expression!r}"
                    )

                complex_type_sets[
                    attribute
                ] = expression

        def normalize_type_set(value: str) -> str:
            complex_expression = (
                complex_type_sets.get(value)
            )

            if complex_expression is not None:
                return complex_expression

            return normalize_symbol(value)

        def render_requirement(
            requirement,
            *,
            source_requirement_id: str,
        ):
            """
            Render one canonical CIL requirement into zero or more
            source-equivalent Android policy statements.

            The returned provenance id always identifies the exact
            canonical CIL requirement that produced the source form.
            """

            form_name = requirement.form_name

            provenance_id = cls._cil_provenance_id(
                source_requirement_id=source_requirement_id,
                form_name=form_name,
                source_line=requirement.source_line,
                end_line=requirement.end_line,
            )

            if form_name in cls._RENDERED_DECLARATIONS:
                declaration_name = None

                if requirement.arguments:
                    declaration_name = cls._atom(
                        requirement.arguments[0]
                    )

                if (
                    form_name == "typeattribute"
                    and declaration_name is not None
                    and declaration_name in complex_type_sets
                ):
                    return (
                        "generated",
                        (),
                        (),
                        provenance_id,
                    )

                statement = cls._render_declaration(
                    requirement,
                    normalize_symbol=normalize_symbol,
                )

                if statement is not None:
                    return (
                        "rendered",
                        (statement,),
                        (),
                        provenance_id,
                    )

                return (
                    "unsupported",
                    (),
                    (),
                    provenance_id,
                )

            if form_name == "typeattributeset":
                statements = cls._render_type_attribute_set(
                    requirement,
                    normalize_symbol=normalize_symbol,
                )

                if statements is not None:
                    return (
                        "rendered",
                        tuple(statements),
                        (),
                        provenance_id,
                    )

                attribute = None

                if requirement.arguments:
                    attribute = cls._atom(
                        requirement.arguments[0]
                    )

                if (
                    attribute is not None
                    and attribute in complex_type_sets
                ):
                    return (
                        "generated",
                        (),
                        (),
                        provenance_id,
                    )

                return (
                    "unsupported",
                    (),
                    (),
                    provenance_id,
                )

            if form_name in cls._RENDERED_ACCESS:
                statement = cls._render_access_rule(
                    requirement,
                    normalize_symbol=normalize_symbol,
                    normalize_type_set=normalize_type_set,
                )

                if statement is not None:
                    return (
                        "rendered",
                        (statement,),
                        (),
                        provenance_id,
                    )

                return (
                    "unsupported",
                    (),
                    (),
                    provenance_id,
                )

            if form_name == "allowx":
                statement = cls._render_allowx(
                    requirement,
                    normalize_symbol=normalize_symbol,
                    normalize_type_set=normalize_type_set,
                )

                if statement is not None:
                    return (
                        "rendered",
                        (statement,),
                        (),
                        provenance_id,
                    )

                return (
                    "unsupported",
                    (),
                    (),
                    provenance_id,
                )

            if form_name == "genfscon":
                statement = cls._render_genfscon(
                    requirement,
                    normalize_symbol=normalize_symbol,
                )

                if statement is not None:
                    return (
                        "rendered",
                        (),
                        (statement,),
                        provenance_id,
                    )

                return (
                    "unsupported",
                    (),
                    (),
                    provenance_id,
                )

            if form_name == "typetransition":
                statement = cls._render_type_transition(
                    requirement,
                    normalize_symbol=normalize_symbol,
                    normalize_type_set=normalize_type_set,
                )

                if statement is not None:
                    return (
                        "rendered",
                        (statement,),
                        (),
                        provenance_id,
                    )

                return (
                    "unsupported",
                    (),
                    (),
                    provenance_id,
                )

            if form_name in cls._GENERATED_FORMS:
                return (
                    "generated",
                    (),
                    (),
                    provenance_id,
                )

            return (
                "unsupported",
                (),
                (),
                provenance_id,
            )

        # ----------------------------------------------------
        # Canonical exported public statement surface.
        #
        # plat_pub_versioned.cil is Android's observed exported
        # platform/system_ext/product interface. Render it through
        # exactly the same source-equivalent machinery used for the
        # effective partition CIL so classification is semantic and
        # syntax-consistent.
        # ----------------------------------------------------

        public_policy_statements = set()
        public_genfs_statements = set()

        if public_requirement is not None:
            for requirement in (
                public_requirement.cil_requirements
            ):
                (
                    outcome,
                    policy_statements,
                    genfs_values,
                    _,
                ) = render_requirement(
                    requirement,
                    source_requirement_id=(
                        public_requirement.requirement_id
                    ),
                )

                if outcome != "rendered":
                    continue

                public_policy_statements.update(
                    policy_statements
                )

                public_genfs_statements.update(
                    genfs_values
                )

        # An explicitly versioned public symbol is also sufficient
        # evidence that its declaration belongs to the public source
        # surface. This protects declaration ownership from unrelated
        # compiler bookkeeping in plat_pub_versioned.cil.
        public_declaration_names = {
            normalize_symbol(value)
            for value in versioned_public_symbols
        }

        rendered_names = set()
        generated_names = set()
        unsupported_names = set()

        rendered_count = 0
        generated_count = 0
        unsupported_count = 0

        if partition == "vendor":
            visibility_names = ("all",)
        else:
            visibility_names = (
                "public",
                "private",
            )

        policy_statements_by_visibility = {
            visibility: set()
            for visibility in visibility_names
        }

        genfs_statements_by_visibility = {
            visibility: set()
            for visibility in visibility_names
        }

        policy_ids_by_visibility = {
            visibility: set()
            for visibility in visibility_names
        }

        genfs_ids_by_visibility = {
            visibility: set()
            for visibility in visibility_names
        }

        for requirement in (
            policy_requirement.cil_requirements
        ):
            form_name = requirement.form_name

            (
                outcome,
                policy_statements,
                genfs_values,
                provenance_id,
            ) = render_requirement(
                requirement,
                source_requirement_id=(
                    policy_requirement.requirement_id
                ),
            )

            if outcome == "generated":
                generated_names.add(form_name)
                generated_count += 1
                continue

            if outcome == "unsupported":
                unsupported_names.add(form_name)
                unsupported_count += 1
                continue

            rendered_names.add(form_name)
            rendered_count += 1

            declaration_name = None

            if (
                form_name
                in cls._RENDERED_DECLARATIONS
                and requirement.arguments
            ):
                declaration_name = cls._atom(
                    requirement.arguments[0]
                )

                if declaration_name is not None:
                    declaration_name = normalize_symbol(
                        declaration_name
                    )

            for statement in policy_statements:
                if partition == "vendor":
                    visibility = "all"
                elif (
                    statement
                    in public_policy_statements
                ):
                    visibility = "public"
                elif (
                    form_name
                    in cls._RENDERED_DECLARATIONS
                    and declaration_name is not None
                    and declaration_name
                    in public_declaration_names
                ):
                    visibility = "public"
                else:
                    visibility = "private"

                policy_statements_by_visibility[
                    visibility
                ].add(statement)

                policy_ids_by_visibility[
                    visibility
                ].add(provenance_id)

            for statement in genfs_values:
                if partition == "vendor":
                    visibility = "all"
                elif (
                    statement
                    in public_genfs_statements
                ):
                    visibility = "public"
                else:
                    visibility = "private"

                genfs_statements_by_visibility[
                    visibility
                ].add(statement)

                genfs_ids_by_visibility[
                    visibility
                ].add(provenance_id)

        source_requirement_id = (
            policy_requirement.requirement_id
        )

        source_representation_id = (
            policy_representation.representation_id
        )

        sepolicy_root = (
            PurePosixPath(
                identity.device_root.as_posix()
            )
            / "sepolicy"
        )

        sources = []

        for visibility in visibility_names:
            statements = (
                policy_statements_by_visibility[
                    visibility
                ]
            )

            contributing_ids = (
                policy_ids_by_visibility[
                    visibility
                ]
            )

            if statements:
                if partition == "vendor":
                    policy_root = (
                        sepolicy_root
                        / "vendor"
                    )

                    filename = (
                        "treeforge_vendor_policy.te"
                    )

                    surface_description = (
                        "vendor"
                    )
                else:
                    policy_root = (
                        sepolicy_root
                        / partition
                        / visibility
                    )

                    filename = (
                        f"treeforge_{partition}_policy.te"
                    )

                    surface_description = (
                        f"{partition} {visibility}"
                    )

                lines = [
                    "# Generated by TreeForge.",
                    "#",
                    (
                        "# Canonical factory-derived "
                        f"{surface_description} "
                        "SELinux policy synthesis."
                    ),
                    "#",
                    (
                        "# Derived from effective "
                        f"{policy_path.name} semantics."
                    ),
                    (
                        "# Public/private ownership is "
                        "derived from canonical "
                        "plat_pub_versioned.cil."
                        if partition != "vendor"
                        else (
                            "# This source preserves the "
                            "effective vendor policy "
                            "semantics."
                        )
                    ),
                    (
                        "# This file does not reproduce "
                        "the OEM's original policy "
                        "macro/file organization."
                    ),
                    "",
                    *sorted(statements),
                    "",
                ]

                if unsupported_names:
                    lines.extend(
                        (
                            "# TreeForge synthesis coverage "
                            "is intentionally PARTIAL.",
                            (
                                "# Unsupported canonical "
                                f"{partition} CIL form "
                                "families:"
                            ),
                        )
                    )

                    lines.extend(
                        f"#   {name}"
                        for name in sorted(
                            unsupported_names
                        )
                    )

                    lines.append("")

                policy_identity_seed = (
                    source_requirement_id
                    + "\0"
                    + source_representation_id
                    + "\0"
                    + partition
                    + "\0"
                    + visibility
                    + "\0policy\0"
                    + "\0".join(
                        sorted(
                            contributing_ids
                        )
                    )
                )

                sources.append(
                    AndroidDeviceTreeDerivedSelinuxSource(
                        derived_source_id=(
                            "device-tree-derived-selinux:"
                            + sha256(
                                policy_identity_seed.encode(
                                    "utf-8"
                                )
                            ).hexdigest()
                        ),
                        destination=(
                            policy_root
                            / filename
                        ),
                        text="\n".join(lines),
                        source_requirement_id=(
                            source_requirement_id
                        ),
                        source_representation_id=(
                            source_representation_id
                        ),
                        contributing_cil_requirement_ids=(
                            tuple(
                                sorted(
                                    contributing_ids
                                )
                            )
                        ),
                    )
                )

            genfs_statements = (
                genfs_statements_by_visibility[
                    visibility
                ]
            )

            genfs_ids = (
                genfs_ids_by_visibility[
                    visibility
                ]
            )

            if genfs_statements:
                if partition == "vendor":
                    genfs_root = (
                        sepolicy_root
                        / "vendor"
                    )

                    surface_description = (
                        "vendor"
                    )
                else:
                    genfs_root = (
                        sepolicy_root
                        / partition
                        / visibility
                    )

                    surface_description = (
                        f"{partition} {visibility}"
                    )

                genfs_lines = [
                    "# Generated by TreeForge.",
                    "#",
                    (
                        "# Canonical factory-derived "
                        f"{surface_description} "
                        "genfs labels."
                    ),
                    "#",
                    (
                        "# Derived from effective "
                        f"{policy_path.name} semantics."
                    ),
                    "",
                    *sorted(genfs_statements),
                    "",
                ]

                genfs_identity_seed = (
                    source_requirement_id
                    + "\0"
                    + source_representation_id
                    + "\0"
                    + partition
                    + "\0"
                    + visibility
                    + "\0genfs_contexts\0"
                    + "\0".join(
                        sorted(
                            genfs_ids
                        )
                    )
                )

                sources.append(
                    AndroidDeviceTreeDerivedSelinuxSource(
                        derived_source_id=(
                            "device-tree-derived-selinux:"
                            + sha256(
                                genfs_identity_seed.encode(
                                    "utf-8"
                                )
                            ).hexdigest()
                        ),
                        destination=(
                            genfs_root
                            / "genfs_contexts"
                        ),
                        text="\n".join(
                            genfs_lines
                        ),
                        source_requirement_id=(
                            source_requirement_id
                        ),
                        source_representation_id=(
                            source_representation_id
                        ),
                        contributing_cil_requirement_ids=(
                            tuple(
                                sorted(
                                    genfs_ids
                                )
                            )
                        ),
                    )
                )

        if not sources:
            return AndroidDeviceTreeEffectiveSelinuxSynthesis(
                unsupported_form_names=(
                    f"<{partition}-cil-without-rendered-source>",
                ),
                unsupported_requirement_count=1,
            )

        return AndroidDeviceTreeEffectiveSelinuxSynthesis(
            sources=tuple(
                sorted(
                    sources,
                    key=lambda value: (
                        value.destination.as_posix()
                    ),
                )
            ),
            rendered_form_names=tuple(
                sorted(rendered_names)
            ),
            generated_form_names=tuple(
                sorted(generated_names)
            ),
            unsupported_form_names=tuple(
                sorted(unsupported_names)
            ),
            rendered_requirement_count=(
                rendered_count
            ),
            generated_requirement_count=(
                generated_count
            ),
            unsupported_requirement_count=(
                unsupported_count
            ),
        )

    @classmethod
    def _representation_for_path(
        cls,
        reconstruction,
        android_path: PurePosixPath,
    ):
        matches = tuple(
            representation
            for representation
            in reconstruction.selinux_source_representations
            if representation.android_path == android_path
        )

        if len(matches) > 1:
            raise ValueError(
                "multiple Reconstruction SELinux representations "
                f"identify {android_path.as_posix()}"
            )

        return matches[0] if matches else None

    @classmethod
    def _universe_requirement_for_path(
        cls,
        universe,
        android_path: PurePosixPath,
    ):
        matches = tuple(
            requirement
            for requirement
            in universe.selinux_requirements
            if (
                requirement.android_path is not None
                and PurePosixPath(
                    requirement.android_path.as_posix()
                )
                == android_path
            )
        )

        if len(matches) > 1:
            raise ValueError(
                "multiple canonical SELinux requirements identify "
                f"{android_path.as_posix()}"
            )

        return matches[0] if matches else None

    @classmethod
    def _atoms(
        cls,
        expression: AndroidSelinuxCilExpression,
    ) -> tuple[str, ...]:
        if isinstance(
            expression,
            AndroidSelinuxCilAtom,
        ):
            return (expression.value,)

        if isinstance(
            expression,
            AndroidSelinuxCilList,
        ):
            result = []

            for item in expression.items:
                result.extend(
                    cls._atoms(item)
                )

            return tuple(result)

        return ()

    @classmethod
    def _atom(
        cls,
        expression: AndroidSelinuxCilExpression,
    ) -> str | None:
        if isinstance(
            expression,
            AndroidSelinuxCilAtom,
        ):
            return expression.value

        return None

    @classmethod
    def _flat_list(
        cls,
        expression: AndroidSelinuxCilExpression,
    ) -> tuple[str, ...] | None:
        if not isinstance(
            expression,
            AndroidSelinuxCilList,
        ):
            return None

        result = []

        for item in expression.items:
            value = cls._atom(item)

            if value is None:
                return None

            result.append(value)

        return tuple(result)

    @classmethod
    def _render_declaration(
        cls,
        requirement,
        *,
        normalize_symbol,
    ) -> str | None:
        arguments = requirement.arguments

        if len(arguments) != 1:
            return None

        name = cls._atom(arguments[0])

        if name is None:
            return None

        name = normalize_symbol(name)

        if requirement.form_name == "type":
            return f"type {name};"

        if requirement.form_name == "typeattribute":
            return f"attribute {name};"

        return None

    @classmethod
    def _render_type_attribute_set(
        cls,
        requirement,
        *,
        normalize_symbol,
    ) -> tuple[str, ...] | None:
        arguments = requirement.arguments

        if len(arguments) != 2:
            return None

        attribute = cls._atom(arguments[0])
        members = cls._flat_list(arguments[1])

        if attribute is None or members is None:
            return None

        attribute = normalize_symbol(attribute)

        return tuple(
            sorted(
                {
                    (
                        "typeattribute "
                        f"{normalize_symbol(member)} "
                        f"{attribute};"
                    )
                    for member in members
                }
            )
        )

    @classmethod
    def _render_access_rule(
        cls,
        requirement,
        *,
        normalize_symbol,
        normalize_type_set,
    ) -> str | None:
        arguments = requirement.arguments

        if len(arguments) != 3:
            return None

        source = cls._atom(arguments[0])
        target = cls._atom(arguments[1])

        class_permissions = arguments[2]

        if (
            source is None
            or target is None
            or not isinstance(
                class_permissions,
                AndroidSelinuxCilList,
            )
            or len(class_permissions.items) != 2
        ):
            return None

        object_class = cls._atom(
            class_permissions.items[0]
        )

        permissions = cls._flat_list(
            class_permissions.items[1]
        )

        if (
            object_class is None
            or permissions is None
            or not permissions
        ):
            return None

        source = normalize_type_set(source)
        target = normalize_type_set(target)
        object_class = normalize_symbol(object_class)

        rendered_permissions = " ".join(
            normalize_symbol(permission)
            for permission in permissions
        )

        return (
            f"{requirement.form_name} "
            f"{source} {target}:"
            f"{object_class} "
            f"{{ {rendered_permissions} }};"
        )

    @classmethod
    def _render_type_transition(
        cls,
        requirement,
        *,
        normalize_symbol,
        normalize_type_set,
    ) -> str | None:
        arguments = requirement.arguments

        if len(arguments) not in {4, 5}:
            return None

        source = cls._atom(arguments[0])
        target = cls._atom(arguments[1])
        object_class = cls._atom(arguments[2])

        if (
            source is None
            or target is None
            or object_class is None
        ):
            return None

        source = normalize_type_set(source)
        target = normalize_type_set(target)
        object_class = normalize_symbol(object_class)

        if len(arguments) == 4:
            result_type = cls._atom(
                arguments[3]
            )

            if result_type is None:
                return None

            result_type = normalize_symbol(
                result_type
            )

            return (
                f"type_transition "
                f"{source} {target}:"
                f"{object_class} "
                f"{result_type};"
            )

        #
        # CIL:
        #
        #   (typetransition source target class "name" result)
        #
        # TE:
        #
        #   type_transition source target:class result "name";
        #
        name = cls._atom(
            arguments[3]
        )

        result_type = cls._atom(
            arguments[4]
        )

        if (
            name is None
            or result_type is None
        ):
            return None

        result_type = normalize_symbol(
            result_type
        )

        escaped = (
            name
            .replace("\\", "\\\\")
            .replace('"', '\\"')
        )

        return (
            f'type_transition '
            f'{source} {target}:'
            f'{object_class} '
            f'{result_type} "{escaped}";'
        )

    @classmethod
    def _render_complex_type_attribute_set(
        cls,
        requirement,
        *,
        normalize_symbol,
    ) -> tuple[str, str] | None:
        """
        Recover source-level TE type-set algebra from the exact complex
        typeattributeset shape emitted by Android checkpolicy/CIL
        compilation:

            (typeattributeset base_typeattr_N
                (and (<positive...>)
                     (not (<negative...>))))

        The result is:

            ("base_typeattr_N", "{ positive -negative ... }")

        Other CIL set algebra remains unsupported rather than guessed.
        """

        arguments = requirement.arguments

        if len(arguments) != 2:
            return None

        attribute = cls._atom(
            arguments[0]
        )
        expression = arguments[1]

        if (
            attribute is None
            or not isinstance(
                expression,
                AndroidSelinuxCilList,
            )
            or len(expression.items) != 3
        ):
            return None

        operator = cls._atom(
            expression.items[0]
        )

        positives = cls._flat_list(
            expression.items[1]
        )

        negative_expression = (
            expression.items[2]
        )

        if (
            operator != "and"
            or positives is None
            or not positives
            or not isinstance(
                negative_expression,
                AndroidSelinuxCilList,
            )
            or len(
                negative_expression.items
            ) != 2
            or cls._atom(
                negative_expression.items[0]
            ) != "not"
        ):
            return None

        negatives = cls._flat_list(
            negative_expression.items[1]
        )

        if negatives is None or not negatives:
            return None

        rendered = []

        rendered.extend(
            normalize_symbol(value)
            for value in positives
        )

        rendered.extend(
            f"-{normalize_symbol(value)}"
            for value in negatives
        )

        return (
            attribute,
            "{ " + " ".join(rendered) + " }",
        )

    @classmethod
    def _render_allowx(
        cls,
        requirement,
        *,
        normalize_symbol,
        normalize_type_set,
    ) -> str | None:
        """
        Convert canonical CIL allowx ioctl permissions into Android
        allowxperm source-policy syntax.

        Supported CIL xperm members:
          - one hexadecimal ioctl value;
          - (range <low> <high>).

        More complex expressions remain unsupported rather than being
        flattened speculatively.
        """

        arguments = requirement.arguments

        if len(arguments) != 3:
            return None

        source = cls._atom(arguments[0])
        target = cls._atom(arguments[1])
        xperm = arguments[2]

        if (
            source is None
            or target is None
            or not isinstance(
                xperm,
                AndroidSelinuxCilList,
            )
            or len(xperm.items) != 3
        ):
            return None

        operation = cls._atom(
            xperm.items[0]
        )

        object_class = cls._atom(
            xperm.items[1]
        )

        values = xperm.items[2]

        if (
            operation != "ioctl"
            or object_class is None
            or not isinstance(
                values,
                AndroidSelinuxCilList,
            )
        ):
            return None

        rendered_values = []

        for value in values.items:
            literal = cls._atom(value)

            if literal is not None:
                if not literal.startswith("0x"):
                    return None

                rendered_values.append(
                    literal
                )
                continue

            if not isinstance(
                value,
                AndroidSelinuxCilList,
            ):
                return None

            if len(value.items) != 3:
                return None

            range_name = cls._atom(
                value.items[0]
            )
            low = cls._atom(
                value.items[1]
            )
            high = cls._atom(
                value.items[2]
            )

            if (
                range_name != "range"
                or low is None
                or high is None
                or not low.startswith("0x")
                or not high.startswith("0x")
            ):
                return None

            rendered_values.append(
                f"{low}-{high}"
            )

        if not rendered_values:
            return None

        return (
            "allowxperm "
            f"{normalize_type_set(source)} "
            f"{normalize_type_set(target)}:"
            f"{normalize_symbol(object_class)} "
            "ioctl { "
            + " ".join(rendered_values)
            + " };"
        )

    @classmethod
    def _render_genfscon(
        cls,
        requirement,
        *,
        normalize_symbol,
    ) -> str | None:
        """
        Convert the canonical Android CIL genfscon shape into the
        genfs_contexts source syntax.

        This deliberately accepts only the normal Android object context
        with an exact single sensitivity whose low/high ranges agree.
        Anything richer stays unsupported.
        """

        arguments = requirement.arguments

        if len(arguments) != 3:
            return None

        filesystem = cls._atom(
            arguments[0]
        )
        path = cls._atom(
            arguments[1]
        )
        context = arguments[2]

        if (
            filesystem is None
            or path is None
            or not isinstance(
                context,
                AndroidSelinuxCilList,
            )
            or len(context.items) != 4
        ):
            return None

        user = cls._atom(
            context.items[0]
        )
        role = cls._atom(
            context.items[1]
        )
        type_name = cls._atom(
            context.items[2]
        )
        level_range = context.items[3]

        if (
            user is None
            or role is None
            or type_name is None
            or not isinstance(
                level_range,
                AndroidSelinuxCilList,
            )
            or len(level_range.items) != 2
        ):
            return None

        low = cls._flat_list(
            level_range.items[0]
        )
        high = cls._flat_list(
            level_range.items[1]
        )

        if (
            low is None
            or high is None
            or low != high
            or len(low) != 1
        ):
            return None

        level = low[0]

        if not level:
            return None

        return (
            f"genfscon {filesystem} {path} "
            f"{user}:{role}:"
            f"{normalize_symbol(type_name)}:"
            f"{level}"
        )

    @staticmethod
    def _cil_provenance_id(
        *,
        source_requirement_id: str,
        form_name: str,
        source_line: int,
        end_line: int,
    ) -> str:
        return (
            f"{source_requirement_id}:cil:"
            f"{source_line}-{end_line}:"
            f"{form_name}"
        )
