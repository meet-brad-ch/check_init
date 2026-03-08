import re
from dataclasses import dataclass

# Regex that matches: string literals, char literals, line comments, block comments
# The order matters: strings/chars must be tried before comments so that
# "//" inside a string is not treated as a comment.
_COMMENT_OR_STRING = re.compile(
    r"""
    "(?:[^"\\]|\\.)*"     # double-quoted string (handles escapes)
    | '(?:[^'\\]|\\.)*'   # single-quoted char literal
    | //[^\n]*             # line comment
    | /\*[\s\S]*?\*/       # block comment (non-greedy)
    """,
    re.VERBOSE,
)


def _replace_comment(m: re.Match) -> str:
    s = m.group(0)
    if s.startswith(("'", '"')):
        return s  # Keep string/char literals
    if s.startswith("//"):
        return ""  # Remove line comment
    # Block comment: preserve newlines for line-number tracking
    return "\n" * s.count("\n")


@dataclass
class Line:
    number: int  # Original 1-based line number
    text: str


def strip_comments(source: str) -> str:
    """Remove C/C++ comments while preserving string literals and line structure."""
    return _COMMENT_OR_STRING.sub(_replace_comment, source)


def join_continuations(source: str) -> str:
    """Join lines ending with backslash continuation."""
    lines = source.split("\n")
    result = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        while line.endswith("\\") and i + 1 < n:
            line = line[:-1] + lines[i + 1]
            i += 1
        result.append(line)
        i += 1
    return "\n".join(result)


def preprocess(source: str) -> list:
    """Preprocess source: strip comments, join continuations, return Lines with original numbers."""
    stripped = strip_comments(source)
    raw_lines = stripped.split("\n")
    result = []
    i = 0
    n = len(raw_lines)
    while i < n:
        orig_line_num = i + 1  # 1-based
        line = raw_lines[i]
        while line.endswith("\\") and i + 1 < n:
            i += 1
            line = line[:-1] + " " + raw_lines[i]
        result.append(Line(number=orig_line_num, text=line))
        i += 1
    return result
