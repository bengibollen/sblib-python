import ldmud

from sblib import runtime


def format_docstring(efun) -> str:
    doc = getattr(efun, "__doc__", None)
    if doc:
        lines = doc.expandtabs().splitlines()
        indent = len(doc)

        for line in lines[1:]:
            stripped = line.lstrip()
            if stripped:
                indent = min(indent, len(line) - len(stripped))

        trimmed = [lines[0].strip()]
        if indent < len(doc):
            for line in lines[1:]:
                trimmed.append(line[indent:].rstrip())

        while trimmed and not trimmed[-1]:
            trimmed.pop()
        while trimmed and not trimmed[0]:
            trimmed.pop(0)

        return "\n".join(trimmed) + "\n"


def python_efun_help(efunname: str) -> str:
    """
    SYNOPSIS
            string python_efun_help(string efunname)

    DESCRIPTION
            Returns the docstring for the given Python efun, if there is any.

    SEE ALSO
            python_reload(E)
    """

    efun = None
    if hasattr(ldmud, "registered_efuns"):
        efun = getattr(ldmud.registered_efuns, efunname, None)
    if efun is None:
        efun = runtime.get_registered_efun(efunname)
    if efun:
        return format_docstring(efun)


def register() -> None:
    runtime.register_efun("python_efun_help", python_efun_help)
