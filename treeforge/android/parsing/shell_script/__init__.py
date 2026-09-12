from __future__ import annotations

from typing import Any


__all__ = (
    "AndroidShellAssignment",
    "AndroidShellClasspathEntry",
    "AndroidShellCommandObservation",
    "AndroidShellExecObservation",
    "AndroidShellScriptParser",
    "AndroidShellScriptParsingError",
    "AndroidShellScriptParsingResult",
    "ParsedAndroidShellScript",
    "is_android_shell_script",
    "shell_interpreter_from_shebang",
)


_MODEL_EXPORTS = frozenset({
    "AndroidShellAssignment",
    "AndroidShellClasspathEntry",
    "AndroidShellCommandObservation",
    "AndroidShellExecObservation",
    "AndroidShellScriptParsingResult",
    "ParsedAndroidShellScript",
})

_PARSER_EXPORTS = frozenset({
    "AndroidShellScriptParser",
    "AndroidShellScriptParsingError",
})

_RECOGNIZER_EXPORTS = frozenset({
    "is_android_shell_script",
    "shell_interpreter_from_shebang",
})


def __getattr__(
    name: str,
) -> Any:
    """
    Lazily expose shell-script family symbols.

    ``source_inventory`` imports the intrinsic recognizer while defining
    AndroidModelSource. Eagerly importing the shell model here would therefore
    create:

        source_inventory
          -> shell_script.recognizer
          -> shell_script.__init__
          -> shell_script.model
          -> source_inventory

    Lazy package exports keep recognition independent of the model that later
    consumes the completed canonical source inventory.
    """

    if name in _MODEL_EXPORTS:
        from treeforge.android.parsing.shell_script import model

        value = getattr(
            model,
            name,
        )

    elif name in _PARSER_EXPORTS:
        from treeforge.android.parsing.shell_script import parser

        value = getattr(
            parser,
            name,
        )

    elif name in _RECOGNIZER_EXPORTS:
        from treeforge.android.parsing.shell_script import recognizer

        value = getattr(
            recognizer,
            name,
        )

    else:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        )

    globals()[
        name
    ] = value

    return value


def __dir__(
) -> list[str]:
    return sorted(
        {
            *globals(),
            *__all__,
        }
    )
