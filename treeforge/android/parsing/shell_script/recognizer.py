from __future__ import annotations

from pathlib import Path, PurePosixPath
import shlex


_SHELL_INTERPRETER_NAMES = frozenset({
    "sh",
    "ash",
    "bash",
    "dash",
    "ksh",
    "mksh",
    "zsh",
})


def shell_interpreter_from_shebang(
    shebang: str,
) -> str | None:
    """
    Return a statically identified shell interpreter from one shebang.

    Recognition is deliberately intrinsic. No Android path or command-name
    allowlist is used to discover scripts themselves.
    """

    if not isinstance(
        shebang,
        str,
    ):
        raise TypeError(
            "shebang must be a string"
        )

    if not shebang.startswith(
        "#!"
    ):
        return None

    payload = shebang[
        2:
    ].strip()

    if not payload:
        return None

    try:
        tokens = shlex.split(
            payload,
            posix=True,
        )
    except ValueError:
        return None

    if not tokens:
        return None

    interpreter = tokens[0]
    name = PurePosixPath(
        interpreter
    ).name

    if name == "env":
        candidates = tuple(
            token
            for token in tokens[1:]
            if not token.startswith("-")
        )

        if not candidates:
            return None

        interpreter = candidates[0]
        name = PurePosixPath(
            interpreter
        ).name

    if name not in _SHELL_INTERPRETER_NAMES:
        return None

    return interpreter


def is_android_shell_script(
    path: Path,
) -> bool:
    """
    Intrinsically recognize a shell-command file.

    A recognized shell shebang is sufficient evidence.

    Android factory images can also contain executable shell command files
    without a shebang. For those, require a conservative combination of
    intrinsic shell syntax:

      * UTF-8 text with no NUL bytes,
      * at least one simple assignment or export assignment, and
      * at least one explicit ``exec`` command.

    No filename, Android command, device, or product allowlist is used.
    This intentionally does not attempt to interpret arbitrary shell.
    """

    if not isinstance(
        path,
        Path,
    ):
        raise TypeError(
            "path must be a Path"
        )

    try:
        payload = path.read_bytes()
    except OSError:
        return False

    if (
        not payload
        or b"\x00" in payload
    ):
        return False

    try:
        raw = payload.decode(
            "utf-8"
        )
    except UnicodeDecodeError:
        return False

    lines = raw.splitlines()

    if not lines:
        return False

    if (
        shell_interpreter_from_shebang(
            lines[0]
        )
        is not None
    ):
        return True

    assignment_seen = False
    exec_seen = False

    for line in lines:
        stripped = line.strip()

        if (
            not stripped
            or stripped.startswith(
                "#"
            )
        ):
            continue

        try:
            tokens = shlex.split(
                line,
                comments=True,
                posix=True,
            )
        except ValueError:
            continue

        if not tokens:
            continue

        assignment_token = None

        if len(tokens) == 1:
            assignment_token = tokens[0]

        elif (
            len(tokens) == 2
            and tokens[0] == "export"
        ):
            assignment_token = tokens[1]

        if (
            assignment_token is not None
            and "=" in assignment_token
        ):
            name = assignment_token.split(
                "=",
                1,
            )[0]

            if (
                name
                and (
                    name[0].isalpha()
                    or name[0] == "_"
                )
                and all(
                    character.isalnum()
                    or character == "_"
                    for character in name
                )
            ):
                assignment_seen = True

        if tokens[0] == "exec":
            exec_seen = True

        if (
            assignment_seen
            and exec_seen
        ):
            return True

    return False
