import re

from .config import (
    CUDA_QUALIFIERS,
    NON_DECL_KEYWORDS,
    SCALAR_TYPES,
    TYPE_MODIFIERS,
    TYPE_PREFIXES,
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
# Matches: class Foo, struct Bar, union U, typedef struct {, struct {, union {, and heads after macro calls such as
# API_CLASS(Sealed) class EXPORT_API Foo
_CLASS_DEF = re.compile(
    r"^(?:[A-Za-z_]\w*\s*\((?:[^()]|\([^()]*\))*\)\s*)*(?:typedef\s+)?(?:template\s*<[^>]*>\s*)?(class|struct|union)(?:\s+(\w+))?"
)

# String and character literals (escapes included); their brackets are not code
_LITERAL = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')

# Arithmetic/bitwise operators after a declarator's name: the line is an expression, not a declaration
_EXPRESSION_OPERATORS = {"*", "/", "%", "+", "-", "<<", ">>", "^", "|", "~", "?", ":"}

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


def _strip_literals(text: str) -> str:
    """Empty the string and character literals, so brackets inside them are not counted."""
    if '"' not in text and "'" not in text:
        return text
    return _LITERAL.sub('""', text)


def _update_depths(text: str, brace_depth: int, paren_depth: int) -> tuple:
    """Update brace/paren depth using str.count (much faster than char iteration)."""
    text = _strip_literals(text)
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
                combined = _strip_literals(combined)
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
        could_be_decl = (first_char.isalpha() or first_char == "_" or text.startswith("::")) and (
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

        # Try to parse as variable declaration (one finding per uninitialized declarator)
        if not in_class or check_members:
            result.findings.extend(_try_parse_declaration(full_text, filepath, line.number, in_class))

        # Update depths and skip consumed lines
        if lines_consumed > 0:
            brace_depth, paren_depth = _update_depths(full_text, brace_depth, paren_depth)
            i += 1 + lines_consumed
        else:
            brace_depth, paren_depth = _update_depths(text, brace_depth, paren_depth)
            i += 1

    return result


def _split_declarators(tokens: list) -> list:
    """Split the tokens after a declaration's type at top-level commas (one list per declarator)."""
    groups = [[]]
    depth = 0
    for t in tokens:
        if t in ("(", "{"):
            depth += 1
        elif t in (")", "}"):
            depth = max(0, depth - 1)
        elif t == "," and depth == 0:
            groups.append([])
            continue
        groups[-1].append(t)
    return groups


def _try_parse_declaration(text: str, filepath: str, line_num: int, in_class: bool) -> list:
    """Parse text as a declaration; returns a finding for each uninitialized declarator (empty if none or not a
    declaration)."""
    semi_idx = text.find(";")
    if semi_idx < 0:
        return []
    decl = text[:semi_idx].strip()
    # A global-scope type (::Type name;) parses as the type itself
    if decl.startswith("::"):
        decl = decl[2:].lstrip()

    if not decl:
        return []

    tokens = _tokenize_and_merge(decl)
    if not tokens:
        return []

    first = tokens[0]

    # Skip non-declaration lines (check base name for scoped identifiers)
    first_base = first.split("::")[-1].split("<")[0] if "::" in first else first.split("<")[0]
    if first_base in NON_DECL_KEYWORDS:
        return []

    # Skip if any keyword that makes this not a decl
    if "extern" in tokens or "typedef" in tokens or "using" in tokens:
        return []

    # Skip assignments and expressions
    if _ASSIGNMENT.match(decl):
        return []

    # Parse: [qualifiers...] type [modifiers...] declarator [, declarator...] ;
    #   declarator: [*/&/&&/qualifiers...] name [array...] [initializer]
    idx = 0

    # Consume qualifiers and prefix words (typename)
    while idx < len(tokens) and (tokens[idx] in _ALL_QUALIFIERS or tokens[idx] in TYPE_PREFIXES):
        idx += 1

    if idx >= len(tokens):
        return []

    # Expect type — any identifier (possibly scoped/templated)
    type_name = tokens[idx]

    # Must look like an identifier or scoped name
    base_type = (
        type_name.split("<")[0].split("::")[-1] if "::" in type_name else type_name.split("<")[0]
    )
    if not _IDENT.match(base_type):
        return []

    if base_type in NON_DECL_KEYWORDS:
        return []

    idx += 1

    # Consume additional type-modifier words for multi-word types
    # e.g. "unsigned long long", "signed char", "long double"
    if type_name in _ALL_TYPE_WORDS:
        while idx < len(tokens) and tokens[idx] in _ALL_TYPE_WORDS:
            idx += 1

    findings = []
    for position, group in enumerate(_split_declarators(tokens[idx:])):
        g = 0
        # Pointer/reference markers and post-type qualifiers belong to the declarator
        has_pointer = False
        while g < len(group) and (group[g] in ("*", "&", "&&") or group[g] in TYPE_QUALIFIERS):
            if group[g] in ("*", "&", "&&"):
                has_pointer = True
            g += 1

        if g >= len(group):
            return []

        # Expect variable name
        name = group[g]
        if not _IDENT.match(name) or name in _SKIP_AS_NAME:
            return []
        g += 1

        rest = group[g:]
        # The first declarator followed by ( is a function declaration or a constructor call
        if position == 0 and rest and rest[0] == "(":
            if len(_split_declarators(tokens[idx:])) == 1:
                return []
            continue

        is_array = False
        initialized = False
        for t in rest:
            if t[0] == "[":
                is_array = True
            elif t in ("=", "{", "("):
                initialized = True
                break
            elif t in _EXPRESSION_OPERATORS:
                # Arithmetic/bitwise operator after name — this is an expression, not a declaration
                # e.g. "width * height * channels;"
                return []
        if initialized:
            continue

        if is_array:
            kind = "array"
        elif has_pointer:
            kind = "pointer"
        elif in_class:
            kind = "member"
        else:
            kind = "local"

        match = re.search(r"" + re.escape(name) + r"", text)
        col = match.start() + 1 if match else 1
        snippet = text.strip()
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."

        findings.append(
            Finding(
                file=filepath,
                line=line_num,
                column=col,
                var_name=name,
                kind=kind,
                snippet=snippet,
            )
        )
    return findings
