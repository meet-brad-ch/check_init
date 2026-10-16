import re

from .config import (
    CUDA_QUALIFIERS,
    NON_DECL_KEYWORDS,
    SCALAR_TYPES,
    TYPE_MODIFIERS,
    TYPE_QUALIFIERS,
)
from .preprocessor import preprocess
from .types import FileResult, Finding

# Pre-merged set for fast lookups in hot paths
_ALL_QUALIFIERS = TYPE_QUALIFIERS | CUDA_QUALIFIERS
_ALL_TYPE_WORDS = SCALAR_TYPES | TYPE_MODIFIERS
_SKIP_AS_NAME = NON_DECL_KEYWORDS | _ALL_QUALIFIERS | SCALAR_TYPES | TYPE_MODIFIERS

_IDENT = re.compile(r"^[A-Za-z_]\w*$")

# Forward declarations: class Foo; struct Bar; enum Baz;
_FORWARD_DECL = re.compile(r"^\s*(class|struct|enum)\s+[A-Za-z_]\w*\s*;")

# For-loop pattern
_FOR_LOOP = re.compile(r"^\s*for\s*\(")

# Catch pattern
_CATCH = re.compile(r"^\s*catch\s*\(")

# Macro definition
_MACRO_DEF = re.compile(r"^\s*#\s*define\b")

# Structured bindings: auto [x, y] = ...
_STRUCTURED_BINDING = re.compile(r"\bauto\s*\[")

# Class/struct definition (not forward decl)
# Matches: class Foo, struct Bar, typedef struct {, struct {
_CLASS_DEF = re.compile(r"^(?:typedef\s+)?(?:template\s*<[^>]*>\s*)?(class|struct)(?:\s+(\w+))?")

# Label pattern: "label:" but not "case X:" or "public:" etc.
_LABEL = re.compile(r"^\s*\w+\s*:\s*$")

# Function pointer: type (*name)(params)
_FUNC_PTR = re.compile(r"^.*\(\s*\*\s*([A-Za-z_]\w*)\s*\)\s*\(.*\)\s*;$")

# Assignment or expression statement (starts with identifier followed by operator)
# NOTE: do NOT include :: here — it's used for scoped type names (std::vector, etc.)
_ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*(\s*(\.|->|<<|>>|\[)|\s*[+\-*/%&|^~!=<>]+=)")

# --- Early rejection: lines that cannot be variable declarations ---
# Must contain a semicolon (declarations end with ;)
# Must start with an identifier-like token (possibly with leading qualifiers)
# Must NOT start with a keyword that rules out a declaration
_COULD_BE_DECL = re.compile(r"^[A-Za-z_].*;\s*$")

# --- Regex-based tokenizer ---
# We use a simple regex for most tokens, but handle template <> with a
# dedicated function to avoid catastrophic backtracking on comparison operators.
_TOKEN_RE = re.compile(
    r"""
    ::                          # scope resolution
    | &&                        # rvalue reference
    | ->                        # arrow (skip)
    | [*&]                      # pointer/reference
    | \[[^\]]*\]                # array dimensions
    | [;{}(),=<>]               # punctuation (< and > handled specially after)
    | [A-Za-z_]\w*              # identifier / keyword
    | \S                        # any other non-space char (skip)
    """,
    re.VERBOSE,
)


def _tokenize_and_merge(text: str) -> list:
    """Tokenize and merge scoped names in one pass.

    Handles template args by collecting balanced <> after identifiers.
    """
    raw = _TOKEN_RE.findall(text)
    # Merge scoped names and template args:
    #   ['std', '::', 'vector', '<', 'int', '>'] -> ['std::vector<int>']
    merged = []
    i = 0
    n = len(raw)
    while i < n:
        tok = raw[i]
        if tok[0].isalpha() or tok[0] == "_":
            # Identifier — look ahead for :: and template <...>
            combined = tok
            while i + 1 < n:
                nxt = raw[i + 1]
                if nxt == "::" and i + 2 < n:
                    combined += "::" + raw[i + 2]
                    i += 2
                elif nxt == "<":
                    # Collect balanced <> as template args
                    tmpl, end = _collect_template_args(raw, i + 1)
                    if tmpl is not None:
                        combined += tmpl
                        i = end
                    else:
                        break
                else:
                    break
            merged.append(combined)
        else:
            merged.append(tok)
        i += 1
    return merged


def _collect_template_args(tokens: list, start: int) -> tuple:
    """Collect balanced <> from token list starting at 'start' (which must be '<').

    Returns (template_string, last_index_consumed) or (None, 0) if unbalanced.
    """
    depth = 0
    parts = []
    i = start
    n = len(tokens)
    while i < n:
        tok = tokens[i]
        if tok == "<":
            depth += 1
            parts.append(tok)
        elif tok == ">":
            depth -= 1
            parts.append(tok)
            if depth == 0:
                return "".join(parts), i
        elif tok == ";":
            # Hit semicolon before closing > — not a template
            return None, 0
        else:
            parts.append(tok)
        i += 1
    # Unbalanced
    return None, 0


def _update_depths(text: str, brace_depth: int, paren_depth: int) -> tuple:
    """Update brace/paren depth using str.count (much faster than char iteration)."""
    open_b = text.count("{")
    close_b = text.count("}")
    open_p = text.count("(")
    close_p = text.count(")")

    # Fast path: no braces or parens at all
    if not (open_b or close_b or open_p or close_p):
        return brace_depth, paren_depth

    # For braces, simple count works when there's no interleaving of open/close
    # that could cause negative depth. Use the safe approach.
    if open_b or close_b:
        # When only opens or only closes, fast path
        if open_b and not close_b:
            brace_depth += open_b
        elif close_b and not open_b:
            brace_depth = max(0, brace_depth - close_b)
        else:
            # Mixed: must iterate to avoid going negative
            for c in text:
                if c == "{":
                    brace_depth += 1
                elif c == "}":
                    brace_depth = max(0, brace_depth - 1)

    if open_p or close_p:
        if open_p and not close_p:
            paren_depth += open_p
        elif close_p and not open_p:
            paren_depth = max(0, paren_depth - close_p)
        else:
            for c in text:
                if c == "(":
                    paren_depth += 1
                elif c == ")":
                    paren_depth = max(0, paren_depth - 1)

    return brace_depth, paren_depth


def scan_file(source: str, filepath: str = "<stdin>", check_members: bool = False) -> FileResult:
    """Scan a C/C++/CUDA source file for uninitialized variable declarations."""
    result = FileResult(path=filepath)
    lines = preprocess(source)

    if not lines:
        return result

    brace_depth = 0
    paren_depth = 0
    class_scope_stack = []  # brace depths where class/struct scope began
    in_macro_def = False

    i = 0
    n_lines = len(lines)
    while i < n_lines:
        line = lines[i]
        text = line.text.strip()

        # A class's scope ends once the brace depth is back where it opened: its closing brace was counted by
        # _update_depths on an earlier line
        while class_scope_stack and brace_depth <= class_scope_stack[-1]:
            class_scope_stack.pop()

        # Skip empty lines
        if not text:
            i += 1
            continue

        # Skip preprocessor directives
        if text[0] == "#":
            if _MACRO_DEF.match(text) and line.text.rstrip().endswith("\\"):
                in_macro_def = True
            i += 1
            continue

        if in_macro_def:
            if not line.text.rstrip().endswith("\\"):
                in_macro_def = False
            i += 1
            continue

        # Track class/struct definitions for member detection
        class_match = _CLASS_DEF.match(text)
        if class_match and not text.rstrip().endswith(";"):
            # Find opening brace (on this line or subsequent)
            combined = text
            j = i
            while "{" not in combined and j + 1 < n_lines and j < i + 5:
                j += 1
                combined += " " + lines[j].text.strip()

            if "{" in combined:
                found_first = False
                for c in combined:
                    if c == "{":
                        if not found_first:
                            class_scope_stack.append(brace_depth)
                            found_first = True
                        brace_depth += 1
                    elif c == "}":
                        brace_depth -= 1
                        if class_scope_stack and class_scope_stack[-1] == brace_depth:
                            class_scope_stack.pop()
                for c in combined:
                    if c == "(":
                        paren_depth += 1
                    elif c == ")":
                        paren_depth = max(0, paren_depth - 1)
                i = j + 1
                continue

        # Skip forward declarations
        if _FORWARD_DECL.match(text):
            i += 1
            continue

        # Skip for-loops and catch blocks
        if _FOR_LOOP.match(text) or _CATCH.match(text):
            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1
            continue

        # Skip structured bindings
        if _STRUCTURED_BINDING.search(text):
            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1
            continue

        # Skip CUDA __shared__ declarations (NVCC forbids initializers on shared memory)
        if "__shared__" in text:
            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1
            continue

        # Skip labels
        if _LABEL.match(text):
            i += 1
            continue

        # Skip if inside parentheses
        if paren_depth > 0:
            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1
            continue

        # Directly in the class body: a method body inside the class is a deeper scope with locals
        in_class = bool(class_scope_stack) and brace_depth == class_scope_stack[-1] + 1

        # --- Early rejection: skip lines that can't be declarations ---
        # Lines without ; that don't need multi-line joining are skipped.
        # Lines starting with non-identifier chars are skipped.
        first_char = text[0]
        could_be_decl = (first_char.isalpha() or first_char == "_") and (
            ";" in text or (not text.endswith("{") and not text.endswith("}"))
        )

        if not could_be_decl:
            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1
            continue

        # Multi-line joining: if line has no terminator, look ahead
        full_text = text
        lines_consumed = 0
        if ";" not in text and not text.endswith("{") and not text.endswith("}"):
            joined = text
            j = i + 1
            lookahead = 0
            while j < n_lines and lookahead < 5:
                nxt = lines[j].text.strip()
                if not nxt:
                    j += 1
                    lookahead += 1
                    lines_consumed += 1
                    continue
                joined += " " + nxt
                lines_consumed += 1
                if ";" in nxt or "{" in nxt:
                    break
                j += 1
                lookahead += 1
            full_text = joined

        # After joining, must have a semicolon to be a declaration
        if ";" not in full_text:
            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1
            continue

        # Check for function pointer declarations
        fp_match = _FUNC_PTR.match(full_text)
        if fp_match:
            var_name = fp_match.group(1)
            if "=" not in full_text.split(")")[-1].split(";")[0]:
                finding = Finding(
                    file=filepath,
                    line=line.number,
                    column=full_text.find(var_name) + 1,
                    var_name=var_name,
                    kind="pointer",
                    snippet=full_text.strip()[:120],
                )
                if in_class and not check_members:
                    pass
                else:
                    result.findings.append(finding)

            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1
            continue

        # Try to parse as variable declaration
        finding = _try_parse_declaration(full_text, filepath, line.number, in_class)
        if finding:
            if in_class and not check_members:
                pass
            else:
                result.findings.append(finding)

        # Update depths and skip consumed lines
        if lines_consumed > 0:
            brace_depth, paren_depth = _update_depths(full_text, brace_depth, paren_depth)
            i += 1 + lines_consumed
        else:
            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1

    return result


def _try_parse_declaration(
    text: str, filepath: str, line_num: int, in_class: bool
) -> "Finding | None":
    """Try to parse text as an uninitialized variable declaration."""
    semi_idx = text.find(";")
    if semi_idx < 0:
        return None
    decl = text[:semi_idx].strip()

    if not decl:
        return None

    tokens = _tokenize_and_merge(decl)
    if not tokens:
        return None

    first = tokens[0]

    # Skip non-declaration lines (check base name for scoped identifiers)
    first_base = first.split("::")[-1].split("<")[0] if "::" in first else first.split("<")[0]
    if first_base in NON_DECL_KEYWORDS:
        return None

    # Skip if any keyword that makes this not a decl
    if "extern" in tokens or "typedef" in tokens or "using" in tokens:
        return None

    # Skip assignments and expressions
    if _ASSIGNMENT.match(text):
        return None

    # Parse: [qualifiers...] type [modifiers...] [*/&/&&...] name [array...] ;
    idx = 0

    # Consume qualifiers
    while idx < len(tokens) and tokens[idx] in _ALL_QUALIFIERS:
        idx += 1

    if idx >= len(tokens):
        return None

    # Expect type — any identifier (possibly scoped/templated)
    type_name = tokens[idx]

    # Must look like an identifier or scoped name
    base_type = (
        type_name.split("<")[0].split("::")[-1] if "::" in type_name else type_name.split("<")[0]
    )
    if not _IDENT.match(base_type):
        return None

    if base_type in NON_DECL_KEYWORDS:
        return None

    idx += 1

    # Consume additional type-modifier words for multi-word types
    # e.g. "unsigned long long", "signed char", "long double"
    if type_name in _ALL_TYPE_WORDS:
        while idx < len(tokens) and tokens[idx] in _ALL_TYPE_WORDS:
            idx += 1

    # Consume pointer/reference markers and post-type qualifiers
    has_pointer = False
    while idx < len(tokens) and (tokens[idx] in ("*", "&", "&&") or tokens[idx] in TYPE_QUALIFIERS):
        if tokens[idx] in ("*", "&", "&&"):
            has_pointer = True
        idx += 1

    if idx >= len(tokens):
        return None

    # Expect variable name
    name = tokens[idx]
    if not _IDENT.match(name):
        return None

    if name in _SKIP_AS_NAME:
        return None

    idx += 1

    # Check what follows the name
    is_array = False
    remaining_tokens = tokens[idx:]

    for t in remaining_tokens:
        if t[0] == "[":
            is_array = True
        elif t in ("=", "{", "("):
            return None  # Has initializer
        elif t == ",":
            break
        elif t in ("*", "/", "%", "+", "-", "<<", ">>", "^", "|", "~", "?", ":"):
            # Arithmetic/bitwise operator after name — this is an expression, not a declaration
            # e.g. "width * height * channels;"
            return None

    # Function declarations: name followed by (
    if remaining_tokens and remaining_tokens[0] == "(":
        return None

    # Determine kind
    if is_array:
        kind = "array"
    elif has_pointer:
        kind = "pointer"
    elif in_class:
        kind = "member"
    else:
        kind = "local"

    col = text.find(name) + 1 if name in text else 1
    snippet = text.strip()
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."

    return Finding(
        file=filepath,
        line=line_num,
        column=col,
        var_name=name,
        kind=kind,
        snippet=snippet,
    )
