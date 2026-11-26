# Copyright (c) 2025-2026 Neil Temperley
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root for full license text.
# https://github.com/neiltemperley/gnuplot-snippets
"""Flexible unrestricted tools for Gnuplot integration with Python."""
import sys
import logging
import re
from collections.abc import Iterable, Iterator

logger = logging.getLogger("gnuplot_snippets")

_TERMINAL_RE = re.compile(r"^\s*set\s+term[inal]*\b", re.IGNORECASE)


def _split_top_level(line: str) -> list[str]:
    """Split one Gnuplot line on ';' outside quotes, braces and comments.
    """
    segments: list[str] = []
    start, depth, quote, i = 0, 0, "", 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 1  # skip escaped character
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            break  # rest of the line is a comment
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            segments.append(line[start:i])
            start = i + 1
        i += 1
    segments.append(line[start:])
    return segments


def _extract_set_terminal_cmd(*set_cmds: str) -> tuple[str | None, list[str]]:
    """Find 'set terminal ...' command(s) if it exists in command(s).

    Commands may be separated by newlines or by semicolons (outside quotes and
    braces). The terminal command is removed from the remaining commands.
    :param set_cmds: Gnuplot commands
    :returns: tuple of set terminal command, list of remaining command lines.
    """
    lines: list[str] = []
    terms: list[str] = []
    for cmd in set_cmds:
        for line in cmd.splitlines():
            if not line.strip():
                continue
            kept: list[str] = []
            for seg in _split_top_level(line):
                if _TERMINAL_RE.match(seg):
                    terms.append(seg.strip())
                elif seg.strip():
                    kept.append(seg.strip())
            if kept:
                lines.append("; ".join(kept))
    if len(terms) > 1:
        raise ValueError(
            f"More than one 'set terminal' command given: {terms}.")
    return (terms[0] if terms else None), lines


def _source(note: str = "", is_snippet: bool = True, depth: int = 2) -> str:
    """Create a comment string identifying the source of a gnuplot command.

    Reports the location ``depth`` frames above this function. The default of 2
    is the caller of the function that called ``_source``, i.e. the user's code
    when called from a public GnuplotSnippets or GnuplotController method.

    Note: No newline at end.
    :param note: optional note to append. Newlines are converted to comment lines.
    :param is_snippet: True if called from a GnuplotSnippets method, else GnuplotController.
    :param depth: number of frames to walk up from this function.
    :returns: Source string to write to the gnuplot script file.
    """
    source_type = "GnuplotSnippets" if is_snippet else "GnuplotController"
    note = note.replace("\n", "\n# ")
    try:
        frame = sys._getframe(depth)
    except (ValueError, AttributeError):  # stack too shallow / non-CPython
        return f"{source_type} Source unknown. {note}"
    filename = frame.f_code.co_filename
    return f"{source_type} Source: {filename}: {frame.f_lineno}: {frame.f_code.co_name}()... {note}"


def _flatten_to_tuple_of_strings(*args) -> tuple[str, ...]:
    """Flatten strings and arbitrarily nested iterables of strings.

    Accepts str, or any iterable (tuple, list, generator, ...) of those, nested to any depth.
    Empty strings are dropped, since plot elements cannot be empty.

    :raises TypeError: if any item is neither a str nor an iterable.
    :returns: tuple of strings
    """

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _flatten(item) -> Iterator[str]:
        if isinstance(item, str):
            yield item
        elif isinstance(item, (bytes, dict)):
            raise TypeError(
                f"plot elements cannot contain {type(item).__name__}")
        elif isinstance(item, Iterable):
            for sub in item:
                yield from _flatten(sub)
        else:
            raise TypeError(
                f"plot elements must be str or iterable of str, got {type(item).__name__}: {item!r}!"
            )

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    return tuple(s for s in _flatten(args) if s.strip())


def _check_cmd(cmd):
    """Check cmd is a string."""
    if not isinstance(cmd, str):
        if type(cmd).__name__ == "GnuplotSnippets":
            raise TypeError(
                f"Expected string, got {type(cmd).__name__}: {cmd!r}.\n"
                "Perhaps you sent a snippets object to preplot()? To add a snippet use the snippets' append() method."
            )
        else:
            raise TypeError(
                f"Expected a string; got {type(cmd).__name__}: {cmd!r}.")
    return


def _clean_cmds(*set_cmds) -> str:
    """Clean and add one or more lines to the gnuplot command string.

    Attempts to comment out any "pause XXX" gnuplot commands of user because
    the GnuplotController will handle the pause workflow.
    :raises TypeError: if any argument is not a string
    :returns: cleaned up command string always ending with a newline unless empty.
    """
    lines: list[str] = []
    for cmd in set_cmds:
        _check_cmd(cmd)
        for line in cmd.splitlines():
            # logger.debug("line     \t= \"{}\"".format(line))
            # Replace 'pause -1', 'pause mouse' with '# pause 0' etc.
            new_line = re.sub(r'\bpause\s+(-?\d+|mouse)([^;\n]*)[;]*',
                              r'# pause \1\2\n', line)
            # logger.debug("new_line \t= \"{}\"".format(new_line))
            lines.append(new_line.rstrip())
    return "\n".join(lines) + "\n" if len(lines) > 0 else ""
