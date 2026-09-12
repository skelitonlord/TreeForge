from __future__ import annotations

from dataclasses import dataclass, field

from treeforge.android.parsing.linker.model import (
    AndroidLinkerConfigurationAssignment,
    AndroidLinkerConfigurationSection,
    ParsedAndroidLinkerConfiguration,
    ParsedAndroidLinkerProtobufConfiguration,
)
from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerDirectoryRoute,
    AndroidUniverseLinkerNamespace,
    AndroidUniverseLinkerNamespaceLink,
    AndroidUniverseLinkerSection,
    AndroidUniverseLinkerTextConfigurationSemantics,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContextResolver,
)


@dataclass
class _MutableLink:
    target_namespace: str
    shared_libs: list[
        str,
    ] = field(
        default_factory=list,
    )
    allow_all_shared_libs: bool = False
    assignments: list[
        AndroidLinkerConfigurationAssignment
    ] = field(
        default_factory=list,
    )


@dataclass
class _MutableNamespace:
    name: str
    isolated: bool = False
    visible: bool = False

    search_paths: list[
        str,
    ] = field(
        default_factory=list,
    )
    permitted_paths: list[
        str,
    ] = field(
        default_factory=list,
    )

    asan_search_paths: list[
        str,
    ] = field(
        default_factory=list,
    )
    asan_permitted_paths: list[
        str,
    ] = field(
        default_factory=list,
    )

    hwasan_search_paths: list[
        str,
    ] = field(
        default_factory=list,
    )
    hwasan_permitted_paths: list[
        str,
    ] = field(
        default_factory=list,
    )

    allowed_libs: list[
        str,
    ] = field(
        default_factory=list,
    )

    links: dict[
        str,
        _MutableLink,
    ] = field(
        default_factory=dict,
    )

    assignments: list[
        AndroidLinkerConfigurationAssignment
    ] = field(
        default_factory=list,
    )

    isolated_seen: bool = False
    visible_seen: bool = False


class AndroidUniverseLinkerTextConfigurationReconciler:
    """
    Interpret canonical ld.config.txt lexical observations.

    This reconciler owns only intra-Linker text configuration semantics.

    It does not:
    - expand runtime variables such as ${LIB};
    - interpret linker.config.pb;
    - interpret native-library policy lists;
    - resolve libraries to ELF objects.
    """

    @staticmethod
    def _split_csv(
        value: str,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            item.strip()
            for item in value.split(
                ","
            )
            if item.strip()
        )

    @staticmethod
    def _split_colon(
        value: str,
    ) -> tuple[
        str,
        ...,
    ]:
        return tuple(
            item.strip()
            for item in value.split(
                ":"
            )
            if item.strip()
        )

    @staticmethod
    def _apply_list_assignment(
        *,
        target: list[
            str,
        ],
        assignment: AndroidLinkerConfigurationAssignment,
        values: tuple[
            str,
            ...,
        ],
    ) -> bool:
        if not values:
            return False

        if assignment.operator == "=":
            if target:
                return False

        elif assignment.operator == "+=":
            if not target:
                return False

        else:
            return False

        target.extend(
            values
        )

        return True

    def reconcile(
        self,
        configuration: ParsedAndroidLinkerConfiguration,
    ) -> AndroidUniverseLinkerTextConfigurationSemantics:
        if not isinstance(
            configuration,
            ParsedAndroidLinkerConfiguration,
        ):
            raise TypeError(
                "configuration must be a ParsedAndroidLinkerConfiguration"
            )

        sections = tuple(
            sorted(
                configuration.sections,
                key=lambda item: (
                    item.source_line
                ),
            )
        )

        assignments = tuple(
            sorted(
                configuration.assignments,
                key=lambda item: (
                    item.source_line
                ),
            )
        )

        section_names = tuple(
            section.name
            for section in sections
        )

        section_name_set = set(
            section_names
        )

        routes_by_section: dict[
            str,
            list[
                AndroidUniverseLinkerDirectoryRoute
            ],
        ] = {
            name: []
            for name in section_names
        }

        assignments_by_section: dict[
            str,
            list[
                AndroidLinkerConfigurationAssignment
            ],
        ] = {
            name: []
            for name in section_names
        }

        consumed_ids: set[
            int
        ] = set()

        # dir.<section> assignments are configuration-level routing
        # declarations. AOSP uses them to create/map the section before
        # parsing the section body.
        for assignment in assignments:
            if not assignment.key.startswith(
                "dir."
            ):
                continue

            section_name = assignment.key[
                len(
                    "dir."
                ):
            ]

            if (
                not section_name
                or section_name not in section_name_set
                or assignment.operator != "="
                or not assignment.value
            ):
                continue

            route = AndroidUniverseLinkerDirectoryRoute(
                section_name=section_name,
                path=assignment.value,
                assignment=assignment,
            )

            routes_by_section[
                section_name
            ].append(
                route
            )

            assignments_by_section[
                section_name
            ].append(
                assignment
            )

            consumed_ids.add(
                id(
                    assignment
                )
            )

        # Section bodies are determined exclusively from Parsing source-line
        # identity. Nothing is reparsed from raw text.
        for index, section in enumerate(
            sections
        ):
            next_line = (
                sections[
                    index + 1
                ].source_line
                if (
                    index + 1
                    < len(
                        sections
                    )
                )
                else None
            )

            for assignment in assignments:
                if id(
                    assignment
                ) in consumed_ids:
                    continue

                if (
                    assignment.source_line
                    <= section.source_line
                ):
                    continue

                if (
                    next_line is not None
                    and assignment.source_line
                    >= next_line
                ):
                    continue

                assignments_by_section[
                    section.name
                ].append(
                    assignment
                )

        semantic_sections: list[
            AndroidUniverseLinkerSection
        ] = []

        for section in sections:
            section_assignments = tuple(
                sorted(
                    assignments_by_section[
                        section.name
                    ],
                    key=lambda item: (
                        item.source_line
                    ),
                )
            )

            namespaces: dict[
                str,
                _MutableNamespace,
            ] = {
                "default": _MutableNamespace(
                    name="default",
                )
            }

            interpreted_section_assignments: list[
                AndroidLinkerConfigurationAssignment
            ] = list(
                route.assignment
                for route in routes_by_section[
                    section.name
                ]
            )

            # additional.namespaces establishes all named namespace identities
            # before namespace property/link interpretation.
            for assignment in section_assignments:
                if assignment.key != "additional.namespaces":
                    continue

                if (
                    assignment.operator != "="
                    or len(
                        namespaces
                    )
                    != 1
                ):
                    continue

                names = self._split_csv(
                    assignment.value
                )

                if (
                    not names
                    or "default" in names
                    or len(
                        names
                    )
                    != len(
                        set(
                            names
                        )
                    )
                    or any(
                        name in namespaces
                        for name in names
                    )
                ):
                    continue

                for name in names:
                    namespaces[
                        name
                    ] = _MutableNamespace(
                        name=name,
                    )

                interpreted_section_assignments.append(
                    assignment
                )

                consumed_ids.add(
                    id(
                        assignment
                    )
                )

            # Interpret namespace properties in exact source order.
            for assignment in section_assignments:
                if id(
                    assignment
                ) in consumed_ids:
                    continue

                if not assignment.key.startswith(
                    "namespace."
                ):
                    continue

                remainder = assignment.key[
                    len(
                        "namespace."
                    ):
                ]

                namespace_name, separator, property_name = (
                    remainder.partition(
                        "."
                    )
                )

                if (
                    not separator
                    or namespace_name not in namespaces
                    or not property_name
                ):
                    continue

                namespace = namespaces[
                    namespace_name
                ]

                interpreted = False

                if property_name in {
                    "isolated",
                    "visible",
                }:
                    if (
                        assignment.operator == "="
                        and assignment.value
                        in {
                            "true",
                            "false",
                        }
                    ):
                        value = (
                            assignment.value
                            == "true"
                        )

                        if property_name == "isolated":
                            if not namespace.isolated_seen:
                                namespace.isolated = value
                                namespace.isolated_seen = True
                                interpreted = True

                        else:
                            if not namespace.visible_seen:
                                namespace.visible = value
                                namespace.visible_seen = True
                                interpreted = True

                elif property_name in {
                    "search.paths",
                    "permitted.paths",
                    "asan.search.paths",
                    "asan.permitted.paths",
                    "hwasan.search.paths",
                    "hwasan.permitted.paths",
                }:
                    target = {
                        "search.paths": (
                            namespace.search_paths
                        ),
                        "permitted.paths": (
                            namespace.permitted_paths
                        ),
                        "asan.search.paths": (
                            namespace.asan_search_paths
                        ),
                        "asan.permitted.paths": (
                            namespace.asan_permitted_paths
                        ),
                        "hwasan.search.paths": (
                            namespace.hwasan_search_paths
                        ),
                        "hwasan.permitted.paths": (
                            namespace.hwasan_permitted_paths
                        ),
                    }[
                        property_name
                    ]

                    interpreted = self._apply_list_assignment(
                        target=target,
                        assignment=assignment,
                        values=(
                            (
                                assignment.value,
                            )
                            if assignment.value
                            else ()
                        ),
                    )

                elif property_name == "allowed_libs":
                    interpreted = self._apply_list_assignment(
                        target=namespace.allowed_libs,
                        assignment=assignment,
                        values=self._split_colon(
                            assignment.value
                        ),
                    )

                elif property_name == "links":
                    if (
                        assignment.operator
                        == "="
                        and not namespace.links
                    ):
                        targets = self._split_csv(
                            assignment.value
                        )

                        if (
                            targets
                            and len(
                                targets
                            )
                            == len(
                                set(
                                    targets
                                )
                            )
                            and all(
                                target_name
                                in namespaces
                                for target_name
                                in targets
                            )
                        ):
                            for target_name in targets:
                                namespace.links[
                                    target_name
                                ] = _MutableLink(
                                    target_namespace=(
                                        target_name
                                    ),
                                )

                            interpreted = True

                elif property_name.startswith(
                    "link."
                ):
                    parts = property_name.split(
                        "."
                    )

                    if len(
                        parts
                    ) == 3:
                        (
                            _,
                            target_name,
                            link_property,
                        ) = parts

                        link = namespace.links.get(
                            target_name
                        )

                        if link is not None:
                            if (
                                link_property
                                == "shared_libs"
                            ):
                                interpreted = (
                                    self._apply_list_assignment(
                                        target=(
                                            link.shared_libs
                                        ),
                                        assignment=assignment,
                                        values=self._split_colon(
                                            assignment.value
                                        ),
                                    )
                                )

                            elif (
                                link_property
                                == "allow_all_shared_libs"
                                and assignment.operator
                                == "="
                                and assignment.value
                                == "true"
                                and not link.allow_all_shared_libs
                            ):
                                link.allow_all_shared_libs = True
                                interpreted = True

                            if interpreted:
                                link.assignments.append(
                                    assignment
                                )

                if interpreted:
                    namespace.assignments.append(
                        assignment
                    )

                    interpreted_section_assignments.append(
                        assignment
                    )

                    consumed_ids.add(
                        id(
                            assignment
                        )
                    )

            immutable_namespaces: list[
                AndroidUniverseLinkerNamespace
            ] = []

            # Keep AOSP semantic convention: default first, then additional
            # namespaces in their declaration order.
            for namespace in namespaces.values():
                links = tuple(
                    AndroidUniverseLinkerNamespaceLink(
                        target_namespace=(
                            link.target_namespace
                        ),
                        shared_libs=tuple(
                            link.shared_libs
                        ),
                        allow_all_shared_libs=(
                            link.allow_all_shared_libs
                        ),
                        assignments=tuple(
                            link.assignments
                        ),
                    )
                    for link in namespace.links.values()
                )

                immutable_namespaces.append(
                    AndroidUniverseLinkerNamespace(
                        name=namespace.name,
                        isolated=namespace.isolated,
                        visible=namespace.visible,
                        search_paths=tuple(
                            namespace.search_paths
                        ),
                        permitted_paths=tuple(
                            namespace.permitted_paths
                        ),
                        asan_search_paths=tuple(
                            namespace.asan_search_paths
                        ),
                        asan_permitted_paths=tuple(
                            namespace.asan_permitted_paths
                        ),
                        hwasan_search_paths=tuple(
                            namespace.hwasan_search_paths
                        ),
                        hwasan_permitted_paths=tuple(
                            namespace.hwasan_permitted_paths
                        ),
                        allowed_libs=tuple(
                            namespace.allowed_libs
                        ),
                        links=links,
                        assignments=tuple(
                            namespace.assignments
                        ),
                    )
                )

            semantic_sections.append(
                AndroidUniverseLinkerSection(
                    source_section=section,
                    directory_routes=tuple(
                        routes_by_section[
                            section.name
                        ]
                    ),
                    namespaces=tuple(
                        immutable_namespaces
                    ),
                    assignments=tuple(
                        sorted(
                            interpreted_section_assignments,
                            key=lambda item: (
                                item.source_line
                            ),
                        )
                    ),
                )
            )

        uninterpreted_assignments = tuple(
            assignment
            for assignment in assignments
            if id(
                assignment
            ) not in consumed_ids
        )

        return AndroidUniverseLinkerTextConfigurationSemantics(
            source=configuration,
            runtime_context=(
                AndroidUniverseRuntimeContextResolver
                .resolve_model_source(
                    configuration.source
                )
            ),
            sections=tuple(
                semantic_sections
            ),
            uninterpreted_assignments=(
                uninterpreted_assignments
            ),
        )

    def reconcile_all(
        self,
        configurations: tuple[
            ParsedAndroidLinkerConfiguration,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseLinkerTextConfigurationSemantics,
        ...,
    ]:
        if not isinstance(
            configurations,
            tuple,
        ):
            raise TypeError(
                "configurations must be a tuple"
            )

        return tuple(
            self.reconcile(
                configuration
            )
            for configuration in configurations
        )


from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerProtobufConfigurationSemantics,
    AndroidUniverseLinkerProtobufContributionSemantics,
    AndroidUniverseLinkerProtobufLibraryPolicy,
    AndroidUniverseLinkerProtobufLibraryPolicyKind,
    AndroidUniverseLinkerProtobufPermittedPath,
    AndroidUniverseLinkerProtobufUsage,
    AndroidUniverseLinkerVisibilityPolicy,
)


class AndroidUniverseLinkerProtobufReconciler:
    """
    Interpret source-local linker.config.pb policy.

    Provider/requirement matching is deliberately deferred until canonical
    namespaces and all Linker policy sources are available.
    """

    @staticmethod
    def _usage(
        configuration: ParsedAndroidLinkerProtobufConfiguration,
    ) -> AndroidUniverseLinkerProtobufUsage:
        path = (
            configuration.source
            .android_path
            .as_posix()
        )

        source_name = (
            configuration.source.source_name
        )

        if (
            path == "/etc/linker.config.pb"
            and source_name.startswith(
                "apex:"
            )
        ):
            return (
                AndroidUniverseLinkerProtobufUsage
                .APEX_LOCAL
            )

        if path in {
            "/system/etc/linker.config.pb",
            "/system_ext/etc/linker.config.pb",
        }:
            return (
                AndroidUniverseLinkerProtobufUsage
                .SYSTEM_CONTEXT
            )

        if path == "/vendor/etc/linker.config.pb":
            return (
                AndroidUniverseLinkerProtobufUsage
                .VENDOR_CONTEXT
            )

        if path == "/product/etc/linker.config.pb":
            return (
                AndroidUniverseLinkerProtobufUsage
                .PRODUCT_CONTEXT
            )

        return (
            AndroidUniverseLinkerProtobufUsage
            .UNCLASSIFIED
        )

    @staticmethod
    def _visibility_policy(
        configuration: ParsedAndroidLinkerProtobufConfiguration,
    ) -> AndroidUniverseLinkerVisibilityPolicy:
        if not configuration.visible_present:
            return (
                AndroidUniverseLinkerVisibilityPolicy
                .DEFAULT_HIDDEN
            )

        if configuration.visible:
            return (
                AndroidUniverseLinkerVisibilityPolicy
                .EXPLICIT_VISIBLE
            )

        return (
            AndroidUniverseLinkerVisibilityPolicy
            .EXPLICIT_HIDDEN
        )

    def reconcile(
        self,
        configuration: ParsedAndroidLinkerProtobufConfiguration,
    ) -> AndroidUniverseLinkerProtobufConfigurationSemantics:
        if not isinstance(
            configuration,
            ParsedAndroidLinkerProtobufConfiguration,
        ):
            raise TypeError(
                "configuration must be a "
                "ParsedAndroidLinkerProtobufConfiguration"
            )

        permitted_paths = tuple(
            AndroidUniverseLinkerProtobufPermittedPath(
                source=configuration,
                index=index,
                path=path,
            )
            for index, path
            in enumerate(
                configuration.permitted_paths
            )
        )

        provided_libraries = tuple(
            AndroidUniverseLinkerProtobufLibraryPolicy(
                source=configuration,
                kind=(
                    AndroidUniverseLinkerProtobufLibraryPolicyKind
                    .PROVIDE
                ),
                index=index,
                library_name=library_name,
            )
            for index, library_name
            in enumerate(
                configuration.provide_libs
            )
        )

        required_libraries = tuple(
            AndroidUniverseLinkerProtobufLibraryPolicy(
                source=configuration,
                kind=(
                    AndroidUniverseLinkerProtobufLibraryPolicyKind
                    .REQUIRE
                ),
                index=index,
                library_name=library_name,
            )
            for index, library_name
            in enumerate(
                configuration.require_libs
            )
        )

        contributions = tuple(
            AndroidUniverseLinkerProtobufContributionSemantics(
                source=configuration,
                index=index,
                contribution=contribution,
            )
            for index, contribution
            in enumerate(
                configuration.contributions
            )
        )

        return (
            AndroidUniverseLinkerProtobufConfigurationSemantics(
                source=configuration,
                runtime_context=(
                    AndroidUniverseRuntimeContextResolver
                    .resolve_model_source(
                        configuration.source
                    )
                ),
                usage=self._usage(
                    configuration
                ),
                visibility_policy=(
                    self._visibility_policy(
                        configuration
                    )
                ),
                effective_visible=(
                    configuration.visible
                ),
                permitted_paths=permitted_paths,
                provided_libraries=provided_libraries,
                required_libraries=required_libraries,
                contributions=contributions,
                unknown_fields=configuration.unknown_fields,
            )
        )

    def reconcile_all(
        self,
        configurations: tuple[
            ParsedAndroidLinkerProtobufConfiguration,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseLinkerProtobufConfigurationSemantics,
        ...,
    ]:
        if not isinstance(
            configurations,
            tuple,
        ):
            raise TypeError(
                "configurations must be a tuple"
            )

        return tuple(
            self.reconcile(
                configuration
            )
            for configuration
            in configurations
        )


from treeforge.android.parsing.linker.model import (
    AndroidNativeLibraryConfigurationDeclaration,
    ParsedAndroidNativeLibraryConfiguration,
)
from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerNativeLibraryBitness,
    AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
    AndroidUniverseLinkerNativeLibraryDeclaration,
    AndroidUniverseLinkerNativeLibraryPolicyKind,
)


class AndroidUniverseLinkerNativeLibraryReconciler:
    """
    Interpret source-local native-library configuration semantics.

    Effective-source selection and cross-policy reconciliation are deliberately
    deferred.
    """

    @staticmethod
    def _policy_kind(
        configuration: ParsedAndroidNativeLibraryConfiguration,
    ) -> AndroidUniverseLinkerNativeLibraryPolicyKind:
        path = (
            configuration.source
            .android_path
            .as_posix()
        )

        name = (
            configuration.source
            .android_path
            .name
        )

        if (
            name == "llndk.libraries.txt"
            or (
                name.startswith(
                    "llndk.libraries."
                )
                and name.endswith(
                    ".txt"
                )
            )
        ):
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .LLNDK
            )

        if name == "vndkcorevariant.libraries.txt":
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .VNDK_CORE_VARIANT
            )

        if (
            name.startswith(
                "vndksp.libraries."
            )
            and name.endswith(
                ".txt"
            )
        ):
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .VNDK_SP
            )

        if (
            name.startswith(
                "vndkcore.libraries."
            )
            and name.endswith(
                ".txt"
            )
        ):
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .VNDK_CORE
            )

        if (
            name.startswith(
                "vndkprivate.libraries."
            )
            and name.endswith(
                ".txt"
            )
        ):
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .VNDK_PRIVATE
            )

        if name == "sanitizer.libraries.txt":
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .SANITIZER
            )

        if (
            name.startswith(
                "public.libraries-"
            )
            and name.endswith(
                ".txt"
            )
        ):
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .EXTENDED_PUBLIC
            )

        if path == "/vendor/etc/public.libraries.txt":
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .VENDOR_PUBLIC
            )

        if path == "/system/etc/public.libraries.txt":
            return (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .SYSTEM_PUBLIC
            )

        return (
            AndroidUniverseLinkerNativeLibraryPolicyKind
            .UNCLASSIFIED
        )

    @staticmethod
    def _interpret_simple(
        configuration: ParsedAndroidNativeLibraryConfiguration,
        declaration: AndroidNativeLibraryConfigurationDeclaration,
    ) -> AndroidUniverseLinkerNativeLibraryDeclaration | None:
        if len(
            declaration.tokens
        ) != 1:
            return None

        return (
            AndroidUniverseLinkerNativeLibraryDeclaration(
                source=configuration,
                source_declaration=declaration,
                library_name=declaration.tokens[0],
                bitness=(
                    AndroidUniverseLinkerNativeLibraryBitness
                    .ALL
                ),
                nopreload=False,
                qualifier_tokens=(),
            )
        )

    @staticmethod
    def _interpret_public(
        configuration: ParsedAndroidNativeLibraryConfiguration,
        declaration: AndroidNativeLibraryConfigurationDeclaration,
    ) -> AndroidUniverseLinkerNativeLibraryDeclaration | None:
        tokens = declaration.tokens

        if (
            not tokens
            or len(
                tokens
            ) > 3
        ):
            return None

        library_name = tokens[0]

        bitness = (
            AndroidUniverseLinkerNativeLibraryBitness
            .ALL
        )

        nopreload = False

        for token in tokens[1:]:
            if token == "nopreload":
                if nopreload:
                    return None

                nopreload = True
                continue

            if token in {
                "32",
                "64",
            }:
                if (
                    bitness
                    is not
                    AndroidUniverseLinkerNativeLibraryBitness
                    .ALL
                ):
                    return None

                bitness = (
                    AndroidUniverseLinkerNativeLibraryBitness
                    .ONLY_32
                    if token == "32"
                    else
                    AndroidUniverseLinkerNativeLibraryBitness
                    .ONLY_64
                )

                continue

            return None

        return (
            AndroidUniverseLinkerNativeLibraryDeclaration(
                source=configuration,
                source_declaration=declaration,
                library_name=library_name,
                bitness=bitness,
                nopreload=nopreload,
                qualifier_tokens=tokens[1:],
            )
        )

    def reconcile(
        self,
        configuration: ParsedAndroidNativeLibraryConfiguration,
    ) -> AndroidUniverseLinkerNativeLibraryConfigurationSemantics:
        if not isinstance(
            configuration,
            ParsedAndroidNativeLibraryConfiguration,
        ):
            raise TypeError(
                "configuration must be a "
                "ParsedAndroidNativeLibraryConfiguration"
            )

        policy_kind = self._policy_kind(
            configuration
        )

        interpreted: list[
            AndroidUniverseLinkerNativeLibraryDeclaration
        ] = []

        uninterpreted: list[
            AndroidNativeLibraryConfigurationDeclaration
        ] = []

        public_policy = policy_kind in {
            AndroidUniverseLinkerNativeLibraryPolicyKind.SYSTEM_PUBLIC,
            AndroidUniverseLinkerNativeLibraryPolicyKind.EXTENDED_PUBLIC,
            AndroidUniverseLinkerNativeLibraryPolicyKind.VENDOR_PUBLIC,
        }

        simple_policy = policy_kind in {
            AndroidUniverseLinkerNativeLibraryPolicyKind.LLNDK,
            AndroidUniverseLinkerNativeLibraryPolicyKind.SANITIZER,
            (
                AndroidUniverseLinkerNativeLibraryPolicyKind
                .VNDK_CORE_VARIANT
            ),
            AndroidUniverseLinkerNativeLibraryPolicyKind.VNDK_SP,
            AndroidUniverseLinkerNativeLibraryPolicyKind.VNDK_CORE,
            AndroidUniverseLinkerNativeLibraryPolicyKind.VNDK_PRIVATE,
        }

        for declaration in configuration.declarations:
            semantic = None

            if public_policy:
                semantic = self._interpret_public(
                    configuration,
                    declaration,
                )

            elif simple_policy:
                semantic = self._interpret_simple(
                    configuration,
                    declaration,
                )

            if semantic is None:
                uninterpreted.append(
                    declaration
                )
            else:
                interpreted.append(
                    semantic
                )

        return (
            AndroidUniverseLinkerNativeLibraryConfigurationSemantics(
                source=configuration,
                runtime_context=(
                    AndroidUniverseRuntimeContextResolver
                    .resolve_model_source(
                        configuration.source
                    )
                ),
                policy_kind=policy_kind,
                declarations=tuple(
                    interpreted
                ),
                uninterpreted_declarations=tuple(
                    uninterpreted
                ),
            )
        )

    def reconcile_all(
        self,
        configurations: tuple[
            ParsedAndroidNativeLibraryConfiguration,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
        ...,
    ]:
        if not isinstance(
            configurations,
            tuple,
        ):
            raise TypeError(
                "configurations must be a tuple"
            )

        return tuple(
            self.reconcile(
                configuration
            )
            for configuration
            in configurations
        )

from treeforge.android.universe.linker.semantics import (
    AndroidUniverseLinkerRuntimePolicy,
)
from treeforge.android.universe.runtime_context import (
    AndroidUniverseRuntimeContext,
    AndroidUniverseRuntimeContextResolver,
)


class AndroidUniverseLinkerRuntimePolicyReconciler:
    """
    Group Linker-local semantics by canonical Android runtime context.

    This is the first unified Linker layer. It preserves all local semantic
    objects exactly and performs no APEX or ELF relationship resolution.
    """

    @staticmethod
    def _same_context(
        left: AndroidUniverseRuntimeContext,
        right: AndroidUniverseRuntimeContext,
    ) -> bool:
        return (
            AndroidUniverseRuntimeContextResolver
            .same_runtime(
                left,
                right,
            )
        )

    def reconcile(
        self,
        text_configurations: tuple[
            AndroidUniverseLinkerTextConfigurationSemantics,
            ...,
        ],
        protobuf_configurations: tuple[
            AndroidUniverseLinkerProtobufConfigurationSemantics,
            ...,
        ],
        native_library_configurations: tuple[
            AndroidUniverseLinkerNativeLibraryConfigurationSemantics,
            ...,
        ],
    ) -> tuple[
        AndroidUniverseLinkerRuntimePolicy,
        ...,
    ]:
        for values, name in (
            (
                text_configurations,
                "text_configurations",
            ),
            (
                protobuf_configurations,
                "protobuf_configurations",
            ),
            (
                native_library_configurations,
                "native_library_configurations",
            ),
        ):
            if not isinstance(
                values,
                tuple,
            ):
                raise TypeError(
                    f"{name} must be a tuple"
                )

        contexts: list[
            AndroidUniverseRuntimeContext
        ] = []

        all_semantics = (
            text_configurations
            + protobuf_configurations
            + native_library_configurations
        )

        for semantic in all_semantics:
            if any(
                self._same_context(
                    semantic.runtime_context,
                    existing,
                )
                for existing in contexts
            ):
                continue

            contexts.append(
                semantic.runtime_context
            )

        policies = tuple(
            AndroidUniverseLinkerRuntimePolicy(
                runtime_context=context,
                text_configurations=tuple(
                    semantic
                    for semantic
                    in text_configurations
                    if self._same_context(
                        semantic.runtime_context,
                        context,
                    )
                ),
                protobuf_configurations=tuple(
                    semantic
                    for semantic
                    in protobuf_configurations
                    if self._same_context(
                        semantic.runtime_context,
                        context,
                    )
                ),
                native_library_configurations=tuple(
                    semantic
                    for semantic
                    in native_library_configurations
                    if self._same_context(
                        semantic.runtime_context,
                        context,
                    )
                ),
            )
            for context in contexts
        )

        accounted_ids = {
            id(
                semantic
            )
            for policy in policies
            for semantic in (
                policy.text_configurations
                + policy.protobuf_configurations
                + policy.native_library_configurations
            )
        }

        source_ids = {
            id(
                semantic
            )
            for semantic
            in all_semantics
        }

        if accounted_ids != source_ids:
            raise ValueError(
                "every Linker semantic configuration must belong "
                "to exactly one runtime policy"
            )

        return policies

