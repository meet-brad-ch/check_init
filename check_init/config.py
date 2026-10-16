SCALAR_TYPES = {
    "bool",
    "char",
    "short",
    "int",
    "long",
    "float",
    "double",
    "int8_t",
    "int16_t",
    "int32_t",
    "int64_t",
    "uint8_t",
    "uint16_t",
    "uint32_t",
    "uint64_t",
    "size_t",
    "ssize_t",
    "ptrdiff_t",
    "wchar_t",
    "char16_t",
    "char32_t",
}

TYPE_QUALIFIERS = {"const", "volatile", "static", "register", "thread_local", "mutable"}

TYPE_MODIFIERS = {"signed", "unsigned", "long", "short"}

# Words that may precede a type name and are not part of it (typename Base::Type name;)
TYPE_PREFIXES = {"typename"}

POINTER_MARKERS = {"*", "&", "&&"}

# CUDA qualifiers that precede type declarations
CUDA_QUALIFIERS = {"__shared__", "__device__", "__constant__", "__managed__"}

# Keywords that indicate a line is NOT a variable declaration
NON_DECL_KEYWORDS = {
    "return",
    "if",
    "else",
    "while",
    "switch",
    "case",
    "break",
    "continue",
    "goto",
    "throw",
    "delete",
    "new",
    "typedef",
    "using",
    "namespace",
    "template",
    "class",
    "struct",
    "enum",
    "union",
    "public",
    "private",
    "protected",
    "friend",
    "virtual",
    "override",
    "final",
    "explicit",
    "operator",
    "try",
    "catch",
    "extern",
    "inline",
    "constexpr",
    "consteval",
    "constinit",
    "concept",
    "requires",
    "co_await",
    "co_yield",
    "co_return",
    "static_assert",
    "static_cast",
    "dynamic_cast",
    "reinterpret_cast",
    "const_cast",
    "#",
}

# Default file extensions to scan
DEFAULT_EXTENSIONS = {".cpp", ".cc", ".h", ".hpp", ".cu", ".cuh", ".c", ".cxx", ".hxx"}

# Default directory/file exclusion patterns
DEFAULT_EXCLUDES = [
    "third_parties/",
    "third_party/",
    "build/",
    "bazel-",
    "cmake-build-",
    ".pb.h",
    ".pb.cc",
    "generated/",
]
