from __future__ import annotations

from collections import defaultdict

from treeforge.android.universe.selinux.cil import (
    AndroidUniverseSelinuxCilRequirement,
    atom_value,
    list_values,
)
from treeforge.android.universe.selinux.policy_graph import (
    AndroidUniverseSelinuxAccessRule,
    AndroidUniverseSelinuxAccessRuleKind,
    AndroidUniverseSelinuxClassCommonRelationship,
    AndroidUniverseSelinuxExtendedAccessRule,
    AndroidUniverseSelinuxExtendedAccessRuleKind,
    AndroidUniverseSelinuxFsUse,
    AndroidUniverseSelinuxGenfsContext,
    AndroidUniverseSelinuxGenfsLabelsVersionConclusion,
    AndroidUniverseSelinuxGenfsLabelsVersionState,
    AndroidUniverseSelinuxHandleUnknown,
    AndroidUniverseSelinuxPolicyGraph,
    AndroidUniverseSelinuxRoleTypeRelationship,
    AndroidUniverseSelinuxSidContext,
    AndroidUniverseSelinuxTypeAliasRelationship,
    AndroidUniverseSelinuxTypeAttributeExpansion,
    AndroidUniverseSelinuxTypeAttributeMembership,
    AndroidUniverseSelinuxTypeTransition,
    AndroidUniverseSelinuxUserRoleRelationship,
)
from treeforge.android.universe.selinux.requirement import (
    AndroidUniverseSelinuxSourceRequirement,
)
from treeforge.android.universe.selinux.symbol import (
    AndroidUniverseSelinuxSymbol,
    AndroidUniverseSelinuxSymbolEvidence,
    AndroidUniverseSelinuxSymbolKind,
)


_DECLARATION_KINDS = {
    "type": (
        AndroidUniverseSelinuxSymbolKind.TYPE
    ),
    "typeattribute": (
        AndroidUniverseSelinuxSymbolKind.TYPE_ATTRIBUTE
    ),
    "typealias": (
        AndroidUniverseSelinuxSymbolKind.TYPE_ALIAS
    ),
    "role": (
        AndroidUniverseSelinuxSymbolKind.ROLE
    ),
    "roleattribute": (
        AndroidUniverseSelinuxSymbolKind.ROLE_ATTRIBUTE
    ),
    "user": (
        AndroidUniverseSelinuxSymbolKind.USER
    ),
    "class": (
        AndroidUniverseSelinuxSymbolKind.CLASS
    ),
    "common": (
        AndroidUniverseSelinuxSymbolKind.COMMON
    ),
    "sid": (
        AndroidUniverseSelinuxSymbolKind.SID
    ),
    "sensitivity": (
        AndroidUniverseSelinuxSymbolKind.SENSITIVITY
    ),
    "category": (
        AndroidUniverseSelinuxSymbolKind.CATEGORY
    ),
}


_ACCESS_RULE_KINDS = {
    "allow": (
        AndroidUniverseSelinuxAccessRuleKind.ALLOW
    ),
    "auditallow": (
        AndroidUniverseSelinuxAccessRuleKind.AUDITALLOW
    ),
    "dontaudit": (
        AndroidUniverseSelinuxAccessRuleKind.DONTAUDIT
    ),
    "neverallow": (
        AndroidUniverseSelinuxAccessRuleKind.NEVERALLOW
    ),
}


_EXTENDED_ACCESS_RULE_KINDS = {
    "allowx": (
        AndroidUniverseSelinuxExtendedAccessRuleKind.ALLOWX
    ),
    "dontauditx": (
        AndroidUniverseSelinuxExtendedAccessRuleKind.DONTAUDITX
    ),
    "neverallowx": (
        AndroidUniverseSelinuxExtendedAccessRuleKind.NEVERALLOWX
    ),
}


_MLS_FORMS = {
    "mls",
    "mlsconstrain",
    "userlevel",
    "userrange",
    "sensitivitycategory",
}


_ORDERING_FORMS = {
    "classorder",
    "sidorder",
    "sensitivityorder",
    "categoryorder",
}


class AndroidUniverseSelinuxReconciler:
    """
    Reconcile promoted SELinux requirements into one canonical policy graph.

    Reconciliation is additive and lossless. It never reparses source files
    and never discards repeated declaration evidence.
    """

    def reconcile(
        self,
        requirements: tuple[
            AndroidUniverseSelinuxSourceRequirement,
            ...,
        ],
    ) -> AndroidUniverseSelinuxPolicyGraph:
        if not isinstance(
            requirements,
            tuple,
        ):
            raise TypeError(
                "requirements must be a tuple"
            )

        symbol_evidence = defaultdict(
            list
        )

        genfs_labels_version_evidence = tuple(
            source
            for source in requirements
            if source.genfs_labels_version is not None
        )

        genfs_labels_version_values = tuple(
            sorted(
                {
                    source.genfs_labels_version
                    for source
                    in genfs_labels_version_evidence
                    if source.genfs_labels_version is not None
                }
            )
        )

        if len(
            genfs_labels_version_values
        ) == 1:
            genfs_labels_version_conclusion = (
                AndroidUniverseSelinuxGenfsLabelsVersionConclusion(
                    state=(
                        AndroidUniverseSelinuxGenfsLabelsVersionState
                        .AGREED
                    ),
                    value=genfs_labels_version_values[0],
                    observed_values=(
                        genfs_labels_version_values
                    ),
                    evidence=(
                        genfs_labels_version_evidence
                    ),
                )
            )
        elif len(
            genfs_labels_version_values
        ) > 1:
            genfs_labels_version_conclusion = (
                AndroidUniverseSelinuxGenfsLabelsVersionConclusion(
                    state=(
                        AndroidUniverseSelinuxGenfsLabelsVersionState
                        .CONFLICTING
                    ),
                    observed_values=(
                        genfs_labels_version_values
                    ),
                    evidence=(
                        genfs_labels_version_evidence
                    ),
                )
            )
        else:
            genfs_labels_version_conclusion = (
                AndroidUniverseSelinuxGenfsLabelsVersionConclusion(
                    state=(
                        AndroidUniverseSelinuxGenfsLabelsVersionState
                        .UNRESOLVED
                    ),
                )
            )

        memberships = []
        expansions = []
        aliases = []
        role_types = []
        user_roles = []
        class_commons = []
        access_rules = []
        extended_access_rules = []
        transitions = []
        genfs_contexts = []
        fs_uses = []
        sid_contexts = []
        handle_unknown = []
        policy_capabilities = []
        mls_requirements = []
        ordering_requirements = []
        other_requirements = []

        context_requirements = []
        seapp_requirements = []
        mac_permissions_requirements = []

        for source in requirements:
            context_requirements.extend(
                source.context_requirements
            )

            seapp_requirements.extend(
                source.seapp_requirements
            )

            mac_permissions_requirements.extend(
                source.mac_permissions_requirements
            )

            for requirement in (
                source.cil_requirements
            ):
                self._collect_cil_requirement(
                    requirement=requirement,
                    symbol_evidence=symbol_evidence,
                    memberships=memberships,
                    expansions=expansions,
                    aliases=aliases,
                    role_types=role_types,
                    user_roles=user_roles,
                    class_commons=class_commons,
                    access_rules=access_rules,
                    extended_access_rules=(
                        extended_access_rules
                    ),
                    transitions=transitions,
                    genfs_contexts=genfs_contexts,
                    fs_uses=fs_uses,
                    sid_contexts=sid_contexts,
                    handle_unknown=handle_unknown,
                    policy_capabilities=(
                        policy_capabilities
                    ),
                    mls_requirements=(
                        mls_requirements
                    ),
                    ordering_requirements=(
                        ordering_requirements
                    ),
                    other_requirements=(
                        other_requirements
                    ),
                )

        symbols = tuple(
            AndroidUniverseSelinuxSymbol(
                kind=kind,
                name=name,
                evidence=tuple(
                    evidence
                ),
            )
            for (
                kind,
                name,
            ), evidence
            in sorted(
                symbol_evidence.items(),
                key=lambda item: (
                    item[0][0].value,
                    item[0][1],
                ),
            )
        )

        return AndroidUniverseSelinuxPolicyGraph(
            genfs_labels_version_conclusion=(
                genfs_labels_version_conclusion
            ),
            symbols=symbols,
            type_attribute_memberships=tuple(
                memberships
            ),
            type_attribute_expansions=tuple(
                expansions
            ),
            type_aliases=tuple(
                aliases
            ),
            role_types=tuple(
                role_types
            ),
            user_roles=tuple(
                user_roles
            ),
            class_commons=tuple(
                class_commons
            ),
            access_rules=tuple(
                access_rules
            ),
            extended_access_rules=tuple(
                extended_access_rules
            ),
            type_transitions=tuple(
                transitions
            ),
            genfs_contexts=tuple(
                genfs_contexts
            ),
            fs_uses=tuple(
                fs_uses
            ),
            sid_contexts=tuple(
                sid_contexts
            ),
            handle_unknown=tuple(
                handle_unknown
            ),
            context_requirements=tuple(
                context_requirements
            ),
            seapp_requirements=tuple(
                seapp_requirements
            ),
            mac_permissions_requirements=tuple(
                mac_permissions_requirements
            ),
            policy_capabilities=tuple(
                policy_capabilities
            ),
            mls_requirements=tuple(
                mls_requirements
            ),
            ordering_requirements=tuple(
                ordering_requirements
            ),
            other_requirements=tuple(
                other_requirements
            ),
        )

    def _collect_cil_requirement(
        self,
        *,
        requirement: AndroidUniverseSelinuxCilRequirement,
        symbol_evidence,
        memberships,
        expansions,
        aliases,
        role_types,
        user_roles,
        class_commons,
        access_rules,
        extended_access_rules,
        transitions,
        genfs_contexts,
        fs_uses,
        sid_contexts,
        handle_unknown,
        policy_capabilities,
        mls_requirements,
        ordering_requirements,
        other_requirements,
    ) -> None:
        name = requirement.form_name
        arguments = requirement.arguments

        declaration_kind = (
            _DECLARATION_KINDS.get(
                name
            )
        )

        if declaration_kind is not None:
            if arguments:
                symbol_name = atom_value(
                    arguments[0]
                )

                if symbol_name is not None:
                    symbol_evidence[
                        (
                            declaration_kind,
                            symbol_name,
                        )
                    ].append(
                        AndroidUniverseSelinuxSymbolEvidence(
                            requirement=requirement
                        )
                    )

                    return

            other_requirements.append(
                requirement
            )
            return

        if name == "typeattributeset":
            if arguments:
                attribute = atom_value(
                    arguments[0]
                )

                if attribute is not None:
                    memberships.append(
                        AndroidUniverseSelinuxTypeAttributeMembership(
                            attribute=attribute,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "expandtypeattribute":
            if len(arguments) >= 2:
                attributes = list_values(
                    arguments[0]
                )

                expand_literal = atom_value(
                    arguments[1]
                )

                if (
                    attributes is not None
                    and expand_literal is not None
                ):
                    normalized_expand = {
                        "true": True,
                        "false": False,
                    }.get(
                        expand_literal
                    )

                    expansions.append(
                        AndroidUniverseSelinuxTypeAttributeExpansion(
                            attributes=attributes,
                            expand_literal=expand_literal,
                            expand=normalized_expand,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "typealiasactual":
            if len(arguments) >= 2:
                alias = atom_value(
                    arguments[0]
                )
                actual = atom_value(
                    arguments[1]
                )

                if alias is not None:
                    aliases.append(
                        AndroidUniverseSelinuxTypeAliasRelationship(
                            alias=alias,
                            actual=actual,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "roletype":
            if len(arguments) >= 2:
                role = atom_value(
                    arguments[0]
                )
                type_name = atom_value(
                    arguments[1]
                )

                if (
                    role is not None
                    and type_name is not None
                ):
                    role_types.append(
                        AndroidUniverseSelinuxRoleTypeRelationship(
                            role=role,
                            type_name=type_name,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "userrole":
            if len(arguments) >= 2:
                user = atom_value(
                    arguments[0]
                )
                role = atom_value(
                    arguments[1]
                )

                if (
                    user is not None
                    and role is not None
                ):
                    user_roles.append(
                        AndroidUniverseSelinuxUserRoleRelationship(
                            user=user,
                            role=role,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "classcommon":
            if len(arguments) >= 2:
                class_name = atom_value(
                    arguments[0]
                )
                common_name = atom_value(
                    arguments[1]
                )

                if (
                    class_name is not None
                    and common_name is not None
                ):
                    class_commons.append(
                        AndroidUniverseSelinuxClassCommonRelationship(
                            class_name=class_name,
                            common_name=common_name,
                            requirement=requirement,
                        )
                    )
                    return

        elif name in _ACCESS_RULE_KINDS:
            if len(arguments) >= 2:
                source = atom_value(
                    arguments[0]
                )
                target = atom_value(
                    arguments[1]
                )

                if (
                    source is not None
                    and target is not None
                ):
                    access_rules.append(
                        AndroidUniverseSelinuxAccessRule(
                            kind=_ACCESS_RULE_KINDS[
                                name
                            ],
                            source=source,
                            target=target,
                            requirement=requirement,
                        )
                    )
                    return

        elif name in _EXTENDED_ACCESS_RULE_KINDS:
            if len(arguments) >= 2:
                source = atom_value(
                    arguments[0]
                )
                target = atom_value(
                    arguments[1]
                )

                if (
                    source is not None
                    and target is not None
                ):
                    extended_access_rules.append(
                        AndroidUniverseSelinuxExtendedAccessRule(
                            kind=(
                                _EXTENDED_ACCESS_RULE_KINDS[
                                    name
                                ]
                            ),
                            source=source,
                            target=target,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "typetransition":
            if len(arguments) >= 4:
                source = atom_value(
                    arguments[0]
                )
                target = atom_value(
                    arguments[1]
                )
                object_class = atom_value(
                    arguments[2]
                )

                transition_name = None
                result_index = 3

                if len(arguments) >= 5:
                    transition_name = atom_value(
                        arguments[3]
                    )
                    result_index = 4

                result_type = atom_value(
                    arguments[
                        result_index
                    ]
                )

                if (
                    source is not None
                    and target is not None
                    and object_class is not None
                    and result_type is not None
                ):
                    transitions.append(
                        AndroidUniverseSelinuxTypeTransition(
                            source=source,
                            target=target,
                            object_class=object_class,
                            result_type=result_type,
                            name=transition_name,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "genfscon":
            if len(arguments) >= 2:
                filesystem = atom_value(
                    arguments[0]
                )
                path = atom_value(
                    arguments[1]
                )

                if (
                    filesystem is not None
                    and path is not None
                ):
                    genfs_contexts.append(
                        AndroidUniverseSelinuxGenfsContext(
                            filesystem=filesystem,
                            path=path,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "fsuse":
            if len(arguments) >= 2:
                behavior = atom_value(
                    arguments[0]
                )
                filesystem = atom_value(
                    arguments[1]
                )

                if (
                    behavior is not None
                    and filesystem is not None
                ):
                    fs_uses.append(
                        AndroidUniverseSelinuxFsUse(
                            behavior=behavior,
                            filesystem=filesystem,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "sidcontext":
            if arguments:
                sid = atom_value(
                    arguments[0]
                )

                if sid is not None:
                    sid_contexts.append(
                        AndroidUniverseSelinuxSidContext(
                            sid=sid,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "handleunknown":
            if arguments:
                value = atom_value(
                    arguments[0]
                )

                if value is not None:
                    handle_unknown.append(
                        AndroidUniverseSelinuxHandleUnknown(
                            value=value,
                            requirement=requirement,
                        )
                    )
                    return

        elif name == "policycap":
            policy_capabilities.append(
                requirement
            )
            return

        elif name in _MLS_FORMS:
            mls_requirements.append(
                requirement
            )
            return

        elif name in _ORDERING_FORMS:
            ordering_requirements.append(
                requirement
            )
            return

        other_requirements.append(
            requirement
        )