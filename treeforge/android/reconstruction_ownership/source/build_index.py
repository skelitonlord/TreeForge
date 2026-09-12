from __future__ import annotations

import glob
import os
from pathlib import Path
import re

from treeforge.android.reconstruction_ownership.source.build_model import (
    AndroidSourceBuildModule,
    AndroidSourceBuildModuleInventory,
    AndroidSourceBuildProperty,
    AndroidSourceBuildPropertyKind,
    AndroidSourceBuildSystem,
)
from treeforge.android.reconstruction_ownership.source.model import (
    AndroidSourceRepository,
    AndroidSourceRepositoryInventory,
)


_SOONG_MODULE_START_RE = re.compile(
    r"""
    (?m)
    ^[ \t]*
    (?P<module_type>[A-Za-z_][A-Za-z0-9_]*)
    [ \t]*
    \{
    """,
    re.VERBOSE,
)

_SOONG_NAME_RE = re.compile(
    r'''
    (?m)
    ^[ \t]*
    name
    [ \t]*:
    [ \t]*
    "(?P<name>(?:\\.|[^"\\])*)"
    [ \t]*,
    ''',
    re.VERBOSE,
)

_MAKE_LOCAL_MODULE_RE = re.compile(
    r"""
    ^[ \t]*
    LOCAL_MODULE
    [ \t]*
    (?P<operator>:=|\+=|\?=|=)
    [ \t]*
    (?P<value>.*?)
    [ \t]*$
    """,
    re.VERBOSE,
)


class AndroidSourceBuildModuleIndexer:
    """
    Build a deterministic build-module index from literal source declarations.

    This indexer deliberately does not:
    - execute Soong;
    - execute Make;
    - evaluate Make variables;
    - infer target-product consumption;
    - infer installed artifact identity;
    - infer source availability from module-name similarity;
    - decide Reconstruction Ownership.

    Active Blueprint module blocks contribute their literal module type and
    literal top-level-looking name property. Intake starts from Android.bp and
    recursively follows literal Blueprint build-list includes.

    Android.mk contributes literal LOCAL_MODULE assignments only.  Variable-
    bearing module names remain unresolved rather than being guessed.
    """

    _BUILD_FILENAMES = frozenset(
        (
            "Android.bp",
            "Android.mk",
        )
    )

    _PRUNED_DIRECTORY_NAMES = frozenset(
        (
            ".git",
            ".repo",
            ".svn",
            "__pycache__",
            "out",
        )
    )

    @classmethod
    def blueprint_module_type_aliases(
        cls,
        inventory: AndroidSourceRepositoryInventory,
        *,
        module_types: frozenset[str],
    ) -> dict[str, str]:
        """
        Recover literal Soong-config custom module-type aliases.

        A declaration such as:

            soong_config_module_type {
                name: "custom_cc_library",
                module_type: "cc_library",
                ...
            }

        establishes source evidence that instances of
        ``custom_cc_library`` use ``cc_library`` as their base module
        implementation.

        Only aliases with exactly one declaration and a literal base module
        type requested by the caller are returned. Conflicting, duplicate,
        non-literal, or unrelated declarations remain unresolved rather than
        being guessed.
        """
        if not isinstance(
            inventory,
            AndroidSourceRepositoryInventory,
        ):
            raise TypeError(
                "inventory must be an "
                "AndroidSourceRepositoryInventory"
            )

        if (
            not isinstance(
                module_types,
                frozenset,
            )
            or not module_types
            or not all(
                isinstance(value, str)
                and value
                and re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*",
                    value,
                )
                is not None
                for value in module_types
            )
        ):
            raise ValueError(
                "module_types must be a non-empty "
                "frozenset of valid Blueprint module-type names"
            )

        declarations: dict[
            str,
            list[str],
        ] = {}

        for path in cls._blueprint_files_for_inventory(
            inventory=inventory,
        ):
            raw = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            if (
                re.search(
                    r"(?m)^[ \t]*"
                    r"soong_config_module_type"
                    r"[ \t]*\{",
                    raw,
                )
                is None
            ):
                continue

            relative = (
                path.relative_to(
                    inventory.checkout_root
                ).as_posix()
            )

            repository = (
                inventory.repository_for_source_path(
                    relative
                )
            )

            if repository is None:
                continue

            discovered = cls._modules_from_blueprint(
                inventory=inventory,
                repository=repository,
                source_path=relative,
                physical_path=path,
            )

            for module in discovered:
                if (
                    module.module_type
                    != "soong_config_module_type"
                ):
                    continue

                base_module_type = (
                    module.literal_string(
                        "module_type"
                    )
                )

                if (
                    base_module_type
                    not in module_types
                ):
                    continue

                declarations.setdefault(
                    module.name,
                    [],
                ).append(
                    base_module_type
                )

        result = {}

        for name in sorted(
            declarations
        ):
            values = declarations[name]

            # Duplicate/conflicting declarations are deliberately
            # unresolved. Soong itself expects one custom module-type
            # definition, so TreeForge must not choose among several.
            if len(values) != 1:
                continue

            result[name] = values[0]

        return result

    @classmethod
    def index_blueprint_module_types(
        cls,
        inventory: AndroidSourceRepositoryInventory,
        *,
        module_types: frozenset[str],
    ) -> AndroidSourceBuildModuleInventory:
        """
        Build a deterministic narrow source-module index for selected
        Blueprint module types.

        This is the same canonical literal Android.bp parser used by the
        general source build index. The optimization is purely intake
        narrowing: Android.bp files that cannot possibly declare one of the
        requested top-level module types are discarded before full module
        parsing.

        This deliberately does not:
        - infer target-product relevance;
        - infer provider selection;
        - infer installed identity;
        - execute Soong;
        - inspect Android.mk, because the requested vocabulary is explicitly
          Blueprint module types.

        The returned build_files population contains only files that actually
        produced at least one requested module.
        """
        if not isinstance(
            inventory,
            AndroidSourceRepositoryInventory,
        ):
            raise TypeError(
                "inventory must be an "
                "AndroidSourceRepositoryInventory"
            )

        if (
            not isinstance(
                module_types,
                frozenset,
            )
            or not module_types
            or not all(
                isinstance(
                    value,
                    str,
                )
                and value
                and re.fullmatch(
                    r"[A-Za-z_][A-Za-z0-9_]*",
                    value,
                )
                is not None
                for value in module_types
            )
        ):
            raise ValueError(
                "module_types must be a non-empty "
                "frozenset of valid Blueprint module-type names"
            )

        type_pattern = re.compile(
            r"(?m)^[ \t]*(?:"
            + "|".join(
                re.escape(
                    value
                )
                for value in sorted(
                    module_types
                )
            )
            + r")[ \t]*\{"
        )

        build_files = []
        modules = []

        for path in cls._blueprint_files_for_inventory(
            inventory=inventory,
        ):
            relative = (
                path.relative_to(
                    inventory.checkout_root
                ).as_posix()
            )

            repository = (
                inventory.repository_for_source_path(
                    relative
                )
            )

            if repository is None:
                continue

            raw = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            if type_pattern.search(
                raw
            ) is None:
                continue

            discovered = (
                cls._modules_from_blueprint(
                    inventory=inventory,
                    repository=repository,
                    source_path=relative,
                    physical_path=path,
                )
            )

            selected = tuple(
                module
                for module in discovered
                if module.module_type in module_types
            )

            if not selected:
                continue

            build_files.append(
                relative
            )

            modules.extend(
                selected
            )

        build_files = tuple(
            sorted(
                set(
                    build_files
                )
            )
        )

        modules = tuple(
            sorted(
                modules,
                key=lambda module: (
                    module.name,
                    module.repository.project_path,
                    module.source_path,
                    module.source_line,
                    module.build_system.value,
                    module.module_type,
                ),
            )
        )

        return AndroidSourceBuildModuleInventory(
            repository_inventory=inventory,
            build_files=build_files,
            modules=modules,
        )

    @classmethod
    def index(
        cls,
        inventory: AndroidSourceRepositoryInventory,
    ) -> AndroidSourceBuildModuleInventory:
        if not isinstance(
            inventory,
            AndroidSourceRepositoryInventory,
        ):
            raise TypeError(
                "inventory must be an "
                "AndroidSourceRepositoryInventory"
            )

        build_files = []
        modules = []

        blueprint_paths = (
            cls._blueprint_files_for_inventory(
                inventory=inventory,
            )
        )

        make_paths = (
            cls._build_files_for_inventory(
                inventory=inventory,
                filenames=frozenset(
                    (
                        "Android.mk",
                    )
                ),
            )
        )

        for (
            path,
            is_blueprint,
        ) in (
            *(
                (
                    path,
                    True,
                )
                for path in blueprint_paths
            ),
            *(
                (
                    path,
                    False,
                )
                for path in make_paths
            ),
        ):
            relative = (
                path.relative_to(
                    inventory.checkout_root
                ).as_posix()
            )

            repository = (
                inventory.repository_for_source_path(
                    relative
                )
            )

            if repository is None:
                continue

            build_files.append(
                relative
            )

            if is_blueprint:
                discovered = (
                    cls._modules_from_blueprint(
                        inventory=inventory,
                        repository=repository,
                        source_path=relative,
                        physical_path=path,
                    )
                )

            else:
                discovered = (
                    cls._modules_from_make(
                        inventory=inventory,
                        repository=repository,
                        source_path=relative,
                        physical_path=path,
                    )
                )

            modules.extend(
                discovered
            )

        build_files = tuple(
            sorted(
                set(
                    build_files
                )
            )
        )

        modules = tuple(
            sorted(
                modules,
                key=lambda module: (
                    module.name,
                    module.repository.project_path,
                    module.source_path,
                    module.source_line,
                    module.build_system.value,
                    module.module_type,
                ),
            )
        )

        return AndroidSourceBuildModuleInventory(
            repository_inventory=inventory,
            build_files=build_files,
            modules=modules,
        )

    @staticmethod
    def _blueprint_without_comments(
        text: str,
    ) -> str:
        """
        Remove Blueprint comments while preserving strings and newlines.

        This permits conservative discovery of top-level literal ``build``
        assignments without treating commented declarations as active source
        evidence.
        """
        result = []

        index = 0

        in_string = False
        escaped = False
        line_comment = False
        block_comment = False

        while index < len(text):
            char = text[index]

            next_char = (
                text[index + 1]
                if index + 1 < len(text)
                else ""
            )

            if line_comment:
                if char == "\n":
                    line_comment = False
                    result.append("\n")
                else:
                    result.append(" ")

                index += 1
                continue

            if block_comment:
                if (
                    char == "*"
                    and next_char == "/"
                ):
                    result.extend(
                        (
                            " ",
                            " ",
                        )
                    )

                    block_comment = False
                    index += 2
                    continue

                if char == "\n":
                    result.append("\n")
                else:
                    result.append(" ")

                index += 1
                continue

            if in_string:
                result.append(char)

                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False

                index += 1
                continue

            if (
                char == "/"
                and next_char == "/"
            ):
                result.extend(
                    (
                        " ",
                        " ",
                    )
                )

                line_comment = True
                index += 2
                continue

            if (
                char == "/"
                and next_char == "*"
            ):
                result.extend(
                    (
                        " ",
                        " ",
                    )
                )

                block_comment = True
                index += 2
                continue

            result.append(char)

            if char == '"':
                in_string = True

            index += 1

        return "".join(
            result
        )

    @staticmethod
    def _matching_blueprint_list(
        text: str,
        open_bracket: int,
    ) -> int | None:
        if (
            open_bracket < 0
            or open_bracket >= len(text)
            or text[open_bracket] != "["
        ):
            return None

        depth = 0

        in_string = False
        escaped = False

        index = open_bracket

        while index < len(text):
            char = text[index]

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False

                index += 1
                continue

            if char == '"':
                in_string = True
                index += 1
                continue

            if char == "[":
                depth += 1

            elif char == "]":
                depth -= 1

                if depth == 0:
                    return index

            index += 1

        return None

    @classmethod
    def _literal_blueprint_build_patterns(
        cls,
        text: str,
    ) -> tuple[
        str,
        ...,
    ]:
        """
        Recover literal paths/globs from local Blueprint ``build`` lists.

        Blueprint may evaluate arbitrary variables and list expressions. This
        source-evidence index deliberately follows only literal list components
        that are directly recoverable from the file itself.
        """
        clean = (
            cls._blueprint_without_comments(
                text
            )
        )

        assignment_re = re.compile(
            r"(?m)"
            r"^[ \t]*"
            r"build"
            r"[ \t]*"
            r"(?:\+=|=)"
            r"[ \t]*"
            r"\["
        )

        string_re = re.compile(
            r'"(?P<value>(?:\\.|[^"\\])*)"'
        )

        result = []

        for match in assignment_re.finditer(
            clean
        ):
            open_bracket = (
                match.end()
                - 1
            )

            close_bracket = (
                cls._matching_blueprint_list(
                    clean,
                    open_bracket,
                )
            )

            if close_bracket is None:
                continue

            body = clean[
                open_bracket + 1:
                close_bracket
            ]

            for string_match in string_re.finditer(
                body
            ):
                value = (
                    cls._decode_soong_string(
                        string_match.group(
                            "value"
                        )
                    )
                )

                if not value:
                    continue

                # Blueprint build entries are interpreted relative to the
                # declaring Blueprint file. Keep TreeForge constrained to
                # checkout-relative source evidence.
                if Path(value).is_absolute():
                    continue

                result.append(
                    value
                )

        return tuple(
            sorted(
                set(
                    result
                )
            )
        )

    @classmethod
    def _blueprint_files_for_inventory(
        cls,
        *,
        inventory: AndroidSourceRepositoryInventory,
    ) -> tuple[
        Path,
        ...,
    ]:
        """
        Discover the active Blueprint file population.

        Every literal Android.bp is an intake root. From those roots, follow
        literal ``build = [...]`` / ``build += [...]`` declarations exactly as
        Blueprint does: relative to the declaring file, with glob expansion,
        recursively.

        Duplicate and cyclic inclusion is collapsed by checkout-relative path.
        Repository provenance is resolved for every included file.
        """
        if not isinstance(
            inventory,
            AndroidSourceRepositoryInventory,
        ):
            raise TypeError(
                "inventory must be an "
                "AndroidSourceRepositoryInventory"
            )

        roots = (
            cls._build_files_for_inventory(
                inventory=inventory,
                filenames=frozenset(
                    (
                        "Android.bp",
                    )
                ),
            )
        )

        by_relative = {}

        queue = list(
            roots
        )

        cursor = 0

        while cursor < len(queue):
            path = queue[cursor]
            cursor += 1

            try:
                relative = (
                    path.relative_to(
                        inventory.checkout_root
                    ).as_posix()
                )
            except ValueError:
                continue

            if relative in by_relative:
                continue

            owner = (
                inventory.repository_for_source_path(
                    relative
                )
            )

            if owner is None:
                continue

            by_relative[
                relative
            ] = path

            raw = path.read_text(
                encoding="utf-8",
                errors="replace",
            )

            patterns = (
                cls._literal_blueprint_build_patterns(
                    raw
                )
            )

            for pattern in patterns:
                absolute_pattern = (
                    path.parent
                    / pattern
                )

                matches = tuple(
                    sorted(
                        (
                            Path(
                                os.path.normpath(
                                    candidate
                                )
                            )
                            for candidate in glob.glob(
                                str(
                                    absolute_pattern
                                ),
                                recursive=True,
                            )
                        ),
                        key=lambda candidate: (
                            candidate.as_posix()
                        ),
                    )
                )

                for candidate in matches:
                    if not candidate.is_file():
                        continue

                    try:
                        candidate_relative = (
                            candidate.relative_to(
                                inventory.checkout_root
                            ).as_posix()
                        )
                    except ValueError:
                        continue

                    if any(
                        part
                        in cls._PRUNED_DIRECTORY_NAMES
                        for part
                        in Path(
                            candidate_relative
                        ).parts
                    ):
                        continue

                    candidate_owner = (
                        inventory
                        .repository_for_source_path(
                            candidate_relative
                        )
                    )

                    if candidate_owner is None:
                        continue

                    if (
                        candidate_relative
                        in by_relative
                    ):
                        continue

                    queue.append(
                        candidate
                    )

        return tuple(
            by_relative[key]
            for key in sorted(
                by_relative
            )
        )

    @classmethod
    def _build_files_for_inventory(
        cls,
        *,
        inventory: AndroidSourceRepositoryInventory,
        filenames: frozenset[str],
    ) -> tuple[
        Path,
        ...,
    ]:
        """
        Discover selected build files with one checkout-wide filesystem walk.

        Repository ownership is resolved only for matching files rather than
        repeatedly while descending every Repo project. This preserves exact
        repository provenance while avoiding one recursive walk per project.
        """
        if not isinstance(
            inventory,
            AndroidSourceRepositoryInventory,
        ):
            raise TypeError(
                "inventory must be an "
                "AndroidSourceRepositoryInventory"
            )

        if (
            not isinstance(
                filenames,
                frozenset,
            )
            or not filenames
            or not all(
                isinstance(name, str) and name
                for name in filenames
            )
        ):
            raise ValueError(
                "filenames must be a non-empty frozenset of strings"
            )

        result = []

        for (
            directory,
            directory_names,
            file_names,
        ) in os.walk(
            inventory.checkout_root,
            topdown=True,
        ):
            directory_names[:] = [
                name
                for name in sorted(
                    directory_names
                )
                if name
                not in cls._PRUNED_DIRECTORY_NAMES
            ]

            directory_path = Path(
                directory
            )

            for filename in sorted(
                file_names
            ):
                if filename not in filenames:
                    continue

                path = (
                    directory_path
                    / filename
                )

                relative = (
                    path.relative_to(
                        inventory.checkout_root
                    ).as_posix()
                )

                if (
                    inventory.repository_for_source_path(
                        relative
                    )
                    is None
                ):
                    continue

                result.append(
                    path
                )

        result.sort(
            key=lambda item: (
                item.relative_to(
                    inventory.checkout_root
                ).as_posix()
            )
        )

        return tuple(
            result
        )

    @classmethod
    def _build_files_for_repository(
        cls,
        *,
        inventory: AndroidSourceRepositoryInventory,
        repository: AndroidSourceRepository,
    ) -> tuple[
        Path,
        ...,
    ]:
        root = repository.checkout_path

        if not root.is_dir():
            return ()

        result = []

        for (
            directory,
            directory_names,
            filenames,
        ) in os.walk(
            root,
            topdown=True,
        ):
            directory_path = Path(
                directory
            )

            try:
                relative_directory = (
                    directory_path.relative_to(
                        inventory.checkout_root
                    ).as_posix()
                )
            except ValueError:
                directory_names[:] = []
                continue

            owner = (
                inventory.repository_for_source_path(
                    relative_directory
                )
            )

            if owner is not repository:
                directory_names[:] = []
                continue

            kept_directories = []

            for name in sorted(
                directory_names
            ):
                if (
                    name
                    in cls._PRUNED_DIRECTORY_NAMES
                ):
                    continue

                candidate = (
                    directory_path
                    / name
                )

                relative_candidate = (
                    candidate.relative_to(
                        inventory.checkout_root
                    ).as_posix()
                )

                candidate_owner = (
                    inventory
                    .repository_for_source_path(
                        relative_candidate
                    )
                )

                if candidate_owner is not repository:
                    continue

                kept_directories.append(
                    name
                )

            directory_names[:] = (
                kept_directories
            )

            for filename in sorted(
                filenames
            ):
                if (
                    filename
                    not in cls._BUILD_FILENAMES
                ):
                    continue

                path = (
                    directory_path
                    / filename
                )

                relative = (
                    path.relative_to(
                        inventory.checkout_root
                    ).as_posix()
                )

                if (
                    inventory.repository_for_source_path(
                        relative
                    )
                    is not repository
                ):
                    continue

                result.append(
                    path
                )

        result.sort(
            key=lambda path: (
                path.relative_to(
                    inventory.checkout_root
                ).as_posix()
            )
        )

        return tuple(
            result
        )

    @classmethod
    def _modules_from_blueprint(
        cls,
        *,
        inventory: AndroidSourceRepositoryInventory,
        repository: AndroidSourceRepository,
        source_path: str,
        physical_path: Path,
    ) -> tuple[
        AndroidSourceBuildModule,
        ...,
    ]:
        text = physical_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        result = []

        for match in _SOONG_MODULE_START_RE.finditer(
            text
        ):
            module_type = match.group(
                "module_type"
            )

            open_brace = (
                match.end()
                - 1
            )

            close_brace = cls._matching_brace(
                text,
                open_brace,
            )

            if close_brace is None:
                continue

            body_start = (
                open_brace
                + 1
            )

            body = text[
                body_start:close_brace
            ]

            # Parse literal module identity from the comment-scrubbed
            # view. The scrubber preserves structural position/newlines,
            # so source provenance remains tied to the original Blueprint
            # block while trailing comments cannot invalidate `name:`.
            name_match = (
                cls._top_level_soong_name(
                    cls._blueprint_without_comments(
                        body
                    )
                )
            )

            if name_match is None:
                continue

            raw_name = (
                name_match.group(
                    "name"
                )
            )

            name = cls._decode_soong_string(
                raw_name
            )

            if not name:
                continue

            source_line = (
                text.count(
                    "\n",
                    0,
                    match.start(),
                )
                + 1
            )

            properties = (
                cls._top_level_soong_properties(
                    body=body,
                    body_start=body_start,
                    full_text=text,
                )
            )

            result.append(
                AndroidSourceBuildModule(
                    name=name,
                    build_system=(
                        AndroidSourceBuildSystem
                        .SOONG
                    ),
                    module_type=module_type,
                    source_path=source_path,
                    source_line=source_line,
                    repository=repository,
                    properties=properties,
                )
            )

        return tuple(
            result
        )

    @classmethod
    def _top_level_soong_properties(
        cls,
        *,
        body: str,
        body_start: int,
        full_text: str,
    ) -> tuple[
        AndroidSourceBuildProperty,
        ...,
    ]:
        return cls._soong_literal_properties(
            body=body,
            body_start=body_start,
            full_text=full_text,
            prefix=(),
        )

    @classmethod
    def _soong_literal_properties(
        cls,
        *,
        body: str,
        body_start: int,
        full_text: str,
        prefix: tuple[str, ...],
    ) -> tuple[
        AndroidSourceBuildProperty,
        ...,
    ]:
        """
        Recover literal Soong property leaves from one property scope.

        Nested map scopes are represented as deterministic dotted property
        paths.  Only literal string, boolean, and string-list leaves are
        retained.  Non-literal expressions remain unresolved and are not
        guessed or evaluated.
        """
        result = []

        index = 0
        length = len(body)

        while index < length:
            index = cls._skip_soong_space_and_comments(
                body,
                index,
            )

            if index >= length:
                break

            name_start = index

            if not (
                body[index].isalpha()
                or body[index] == "_"
            ):
                index += 1
                continue

            index += 1

            while (
                index < length
                and (
                    body[index].isalnum()
                    or body[index] == "_"
                )
            ):
                index += 1

            name = body[name_start:index]

            after_name = cls._skip_soong_space_and_comments(
                body,
                index,
            )

            if (
                after_name >= length
                or body[after_name] != ":"
            ):
                index = after_name
                continue

            value_start = cls._skip_soong_space_and_comments(
                body,
                after_name + 1,
            )

            property_line = (
                full_text.count(
                    "\n",
                    0,
                    body_start + name_start,
                )
                + 1
            )

            parsed = cls._parse_soong_literal_property_value(
                body,
                value_start,
            )

            property_path = ".".join(
                (*prefix, name)
            )

            if parsed is not None:
                (
                    kind,
                    value,
                    value_end,
                ) = parsed

                result.append(
                    AndroidSourceBuildProperty(
                        name=property_path,
                        kind=kind,
                        value=value,
                        source_line=property_line,
                    )
                )

                index = cls._skip_soong_expression(
                    body,
                    value_end,
                )
                continue

            if (
                value_start < length
                and body[value_start] == "{"
            ):
                close_brace = cls._matching_brace(
                    body,
                    value_start,
                )

                if close_brace is not None:
                    nested_body_start = (
                        body_start
                        + value_start
                        + 1
                    )

                    nested = cls._soong_literal_properties(
                        body=body[
                            value_start + 1:close_brace
                        ],
                        body_start=nested_body_start,
                        full_text=full_text,
                        prefix=(
                            *prefix,
                            name,
                        ),
                    )

                    result.extend(nested)

                    index = cls._skip_soong_expression(
                        body,
                        close_brace + 1,
                    )
                    continue

            if (
                value_start < length
                and body[value_start] == "["
            ):
                nested_list = (
                    cls._soong_literal_struct_list_properties(
                        body=body,
                        value_start=value_start,
                        body_start=body_start,
                        full_text=full_text,
                        prefix=(
                            *prefix,
                            name,
                        ),
                    )
                )

                if nested_list is not None:
                    nested, value_end = nested_list

                    result.extend(
                        nested
                    )

                    index = cls._skip_soong_expression(
                        body,
                        value_end,
                    )
                    continue

            index = cls._skip_soong_expression(
                body,
                value_start,
            )

        return tuple(
            sorted(
                result,
                key=lambda prop: (
                    prop.source_line,
                    prop.name,
                ),
            )
        )

    @classmethod
    def _soong_literal_struct_list_properties(
        cls,
        *,
        body: str,
        value_start: int,
        body_start: int,
        full_text: str,
        prefix: tuple[str, ...],
    ):
        """
        Recover literal leaves from a Soong list of struct/map values.

        Element order is preserved explicitly in each dotted property path:

            items.0.name
            items.0.values
            items.1.name

        Only literal leaves already supported by AndroidSourceBuildProperty
        are retained. Mixed/non-struct list expressions remain unresolved.
        """
        if (
            value_start >= len(body)
            or body[value_start] != "["
        ):
            return None

        index = value_start + 1
        element_index = 0
        result = []

        while True:
            index = cls._skip_soong_space_and_comments(
                body,
                index,
            )

            if index >= len(body):
                return None

            if body[index] == "]":
                return (
                    tuple(
                        sorted(
                            result,
                            key=lambda prop: (
                                prop.source_line,
                                prop.name,
                            ),
                        )
                    ),
                    index + 1,
                )

            if body[index] != "{":
                return None

            close_brace = cls._matching_brace(
                body,
                index,
            )

            if close_brace is None:
                return None

            nested = cls._soong_literal_properties(
                body=body[
                    index + 1:close_brace
                ],
                body_start=(
                    body_start
                    + index
                    + 1
                ),
                full_text=full_text,
                prefix=(
                    *prefix,
                    str(element_index),
                ),
            )

            result.extend(
                nested
            )

            element_index += 1

            index = cls._skip_soong_space_and_comments(
                body,
                close_brace + 1,
            )

            if index >= len(body):
                return None

            if body[index] == ",":
                index += 1
                continue

            if body[index] == "]":
                return (
                    tuple(
                        sorted(
                            result,
                            key=lambda prop: (
                                prop.source_line,
                                prop.name,
                            ),
                        )
                    ),
                    index + 1,
                )

            return None


    @classmethod
    def _parse_soong_literal_property_value(
        cls,
        text: str,
        start: int,
    ):
        if start >= len(
            text
        ):
            return None

        if text.startswith(
            "true",
            start,
        ) and cls._soong_token_boundary(
            text,
            start + 4,
        ):
            return (
                AndroidSourceBuildPropertyKind.BOOLEAN,
                True,
                start + 4,
            )

        if text.startswith(
            "false",
            start,
        ) and cls._soong_token_boundary(
            text,
            start + 5,
        ):
            return (
                AndroidSourceBuildPropertyKind.BOOLEAN,
                False,
                start + 5,
            )

        if text[start] == '"':
            parsed = cls._parse_soong_string(
                text,
                start,
            )

            if parsed is None:
                return None

            value, end = parsed

            return (
                AndroidSourceBuildPropertyKind.STRING,
                value,
                end,
            )

        if text[start] != "[":
            return None

        index = (
            start
            + 1
        )

        values = []

        while True:
            index = cls._skip_soong_space_and_comments(
                text,
                index,
            )

            if index >= len(
                text
            ):
                return None

            if text[index] == "]":
                return (
                    AndroidSourceBuildPropertyKind.STRING_LIST,
                    tuple(
                        values
                    ),
                    index + 1,
                )

            if text[index] != '"':
                return None

            parsed = cls._parse_soong_string(
                text,
                index,
            )

            if parsed is None:
                return None

            value, index = parsed

            values.append(
                value
            )

            index = cls._skip_soong_space_and_comments(
                text,
                index,
            )

            if index >= len(
                text
            ):
                return None

            if text[index] == ",":
                index += 1
                continue

            if text[index] == "]":
                return (
                    AndroidSourceBuildPropertyKind.STRING_LIST,
                    tuple(
                        values
                    ),
                    index + 1,
                )

            return None

    @classmethod
    def _parse_soong_string(
        cls,
        text: str,
        start: int,
    ) -> tuple[
        str,
        int,
    ] | None:
        if (
            start >= len(text)
            or text[start] != '"'
        ):
            return None

        index = (
            start
            + 1
        )

        escaped = False

        while index < len(
            text
        ):
            char = text[
                index
            ]

            if escaped:
                escaped = False
                index += 1
                continue

            if char == "\\":
                escaped = True
                index += 1
                continue

            if char == '"':
                raw = text[
                    start + 1:index
                ]

                value = (
                    cls._decode_soong_string(
                        raw
                    )
                )

                if value is None:
                    return None

                return (
                    value,
                    index + 1,
                )

            index += 1

        return None

    @staticmethod
    def _soong_token_boundary(
        text: str,
        index: int,
    ) -> bool:
        if index >= len(
            text
        ):
            return True

        char = text[
            index
        ]

        return not (
            char.isalnum()
            or char == "_"
        )

    @classmethod
    def _skip_soong_space_and_comments(
        cls,
        text: str,
        start: int,
    ) -> int:
        index = start

        while index < len(
            text
        ):
            if text[
                index
            ].isspace():
                index += 1
                continue

            if text.startswith(
                "//",
                index,
            ):
                newline = text.find(
                    "\n",
                    index + 2,
                )

                if newline < 0:
                    return len(
                        text
                    )

                index = (
                    newline
                    + 1
                )
                continue

            if text.startswith(
                "/*",
                index,
            ):
                end = text.find(
                    "*/",
                    index + 2,
                )

                if end < 0:
                    return len(
                        text
                    )

                index = (
                    end
                    + 2
                )
                continue

            break

        return index

    @classmethod
    def _skip_soong_expression(
        cls,
        text: str,
        start: int,
    ) -> int:
        index = start

        braces = 0
        brackets = 0
        parentheses = 0

        in_string = False
        escaped = False
        line_comment = False
        block_comment = False

        while index < len(
            text
        ):
            char = text[
                index
            ]

            next_char = (
                text[
                    index + 1
                ]
                if (
                    index + 1
                    < len(text)
                )
                else ""
            )

            if line_comment:
                if char == "\n":
                    line_comment = False

                index += 1
                continue

            if block_comment:
                if (
                    char == "*"
                    and next_char == "/"
                ):
                    block_comment = False
                    index += 2
                    continue

                index += 1
                continue

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False

                index += 1
                continue

            if (
                char == "/"
                and next_char == "/"
            ):
                line_comment = True
                index += 2
                continue

            if (
                char == "/"
                and next_char == "*"
            ):
                block_comment = True
                index += 2
                continue

            if char == '"':
                in_string = True
                index += 1
                continue

            if char == "{":
                braces += 1

            elif char == "}":
                if braces > 0:
                    braces -= 1

            elif char == "[":
                brackets += 1

            elif char == "]":
                if brackets > 0:
                    brackets -= 1

            elif char == "(":
                parentheses += 1

            elif char == ")":
                if parentheses > 0:
                    parentheses -= 1

            elif (
                char == ","
                and braces == 0
                and brackets == 0
                and parentheses == 0
            ):
                return (
                    index
                    + 1
                )

            index += 1

        return index

    @classmethod
    def _top_level_soong_name(
        cls,
        body: str,
    ):
        depth = 0
        index = 0

        in_string = False
        escaped = False
        line_comment = False
        block_comment = False

        line_start = 0

        while index < len(
            body
        ):
            char = body[
                index
            ]

            next_char = (
                body[
                    index + 1
                ]
                if (
                    index + 1
                    < len(body)
                )
                else ""
            )

            if line_comment:
                if char == "\n":
                    line_comment = False
                    line_start = (
                        index
                        + 1
                    )

                index += 1
                continue

            if block_comment:
                if (
                    char == "*"
                    and next_char == "/"
                ):
                    block_comment = False
                    index += 2
                    continue

                if char == "\n":
                    line_start = (
                        index
                        + 1
                    )

                index += 1
                continue

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False

                if char == "\n":
                    line_start = (
                        index
                        + 1
                    )

                index += 1
                continue

            if (
                char == "/"
                and next_char == "/"
            ):
                line_comment = True
                index += 2
                continue

            if (
                char == "/"
                and next_char == "*"
            ):
                block_comment = True
                index += 2
                continue

            if char == '"':
                in_string = True
                index += 1
                continue

            if char in (
                "{",
                "[",
                "(",
            ):
                depth += 1
                index += 1
                continue

            if char in (
                "}",
                "]",
                ")",
            ):
                depth = max(
                    depth - 1,
                    0,
                )
                index += 1
                continue

            if char == "\n":
                if depth == 0:
                    line = body[
                        line_start:index
                    ]

                    match = (
                        _SOONG_NAME_RE.match(
                            line
                        )
                    )

                    if match is not None:
                        return match

                line_start = (
                    index
                    + 1
                )

            index += 1

        if depth == 0:
            line = body[
                line_start:
            ]

            match = (
                _SOONG_NAME_RE.match(
                    line
                )
            )

            if match is not None:
                return match

        return None

    @staticmethod
    def _decode_soong_string(
        value: str,
    ) -> str | None:
        if not isinstance(
            value,
            str,
        ):
            return None

        try:
            decoded = bytes(
                value,
                "utf-8",
            ).decode(
                "unicode_escape"
            )
        except UnicodeDecodeError:
            return None

        return (
            decoded
            if decoded
            else None
        )

    @staticmethod
    def _matching_brace(
        text: str,
        open_brace: int,
    ) -> int | None:
        if (
            open_brace < 0
            or open_brace >= len(text)
            or text[open_brace] != "{"
        ):
            return None

        depth = 0

        in_string = False
        escaped = False
        line_comment = False
        block_comment = False

        index = open_brace

        while index < len(
            text
        ):
            char = text[
                index
            ]

            next_char = (
                text[
                    index + 1
                ]
                if (
                    index + 1
                    < len(text)
                )
                else ""
            )

            if line_comment:
                if char == "\n":
                    line_comment = False

                index += 1
                continue

            if block_comment:
                if (
                    char == "*"
                    and next_char == "/"
                ):
                    block_comment = False
                    index += 2
                    continue

                index += 1
                continue

            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False

                index += 1
                continue

            if (
                char == "/"
                and next_char == "/"
            ):
                line_comment = True
                index += 2
                continue

            if (
                char == "/"
                and next_char == "*"
            ):
                block_comment = True
                index += 2
                continue

            if char == '"':
                in_string = True
                index += 1
                continue

            if char == "{":
                depth += 1

            elif char == "}":
                depth -= 1

                if depth == 0:
                    return index

            index += 1

        return None

    @classmethod
    def _modules_from_make(
        cls,
        *,
        inventory: AndroidSourceRepositoryInventory,
        repository: AndroidSourceRepository,
        source_path: str,
        physical_path: Path,
    ) -> tuple[
        AndroidSourceBuildModule,
        ...,
    ]:
        lines = physical_path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        result = []

        logical_lines = []
        buffer = []
        start_line = None

        for line_number, raw in enumerate(
            lines,
            start=1,
        ):
            if start_line is None:
                start_line = line_number

            buffer.append(
                raw
            )

            if raw.rstrip().endswith(
                "\\"
            ):
                continue

            logical_lines.append(
                (
                    start_line,
                    " ".join(
                        part.rstrip()
                        .removesuffix("\\")
                        for part in buffer
                    ),
                )
            )

            buffer = []
            start_line = None

        if buffer:
            logical_lines.append(
                (
                    start_line
                    or len(lines)
                    or 1,
                    " ".join(
                        part.rstrip()
                        .removesuffix("\\")
                        for part in buffer
                    ),
                )
            )

        for (
            line_number,
            expression,
        ) in logical_lines:
            stripped = (
                expression.strip()
            )

            if (
                not stripped
                or stripped.startswith(
                    "#"
                )
            ):
                continue

            match = (
                _MAKE_LOCAL_MODULE_RE.match(
                    expression
                )
            )

            if match is None:
                continue

            value = (
                match.group(
                    "value"
                )
                .split(
                    "#",
                    1,
                )[0]
                .strip()
            )

            if (
                not value
                or "$" in value
                or any(
                    character.isspace()
                    for character in value
                )
            ):
                continue

            result.append(
                AndroidSourceBuildModule(
                    name=value,
                    build_system=(
                        AndroidSourceBuildSystem
                        .MAKE
                    ),
                    module_type=(
                        "android_make"
                    ),
                    source_path=source_path,
                    source_line=line_number,
                    repository=repository,
                )
            )

        return tuple(
            result
        )
