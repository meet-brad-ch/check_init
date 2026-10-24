# check-init

[![CI](https://github.com/meet-brad-ch/check_init/actions/workflows/ci.yml/badge.svg)](https://github.com/meet-brad-ch/check_init/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Runtime dependencies](https://img.shields.io/badge/runtime%20dependencies-none-brightgreen)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A fast, zero-dependency static analysis tool that detects uninitialized C/C++/CUDA variable declarations.

Unlike compiler-based tools (clang-tidy), `check-init` uses regex-based parsing and requires no build artifacts or `compile_commands.json`. It scans source files directly and runs in seconds on large codebases.

## Installation

```bash
pip install .
```

For development:

```bash
pip install -e .
```

## Usage

```bash
# Scan directories
check-init src/ include/

# Scan specific files
check-init main.cpp utils.h

# Exclude paths
check-init --exclude third_party/ --exclude build/ src/

# JSON output
check-init --json src/ > results.json

# Fail CI if findings exist
check-init --fail-on-findings src/

# Also check class/struct members
check-init --members src/

# Scan only specific extensions
check-init --include-ext .cpp,.cu src/

# Quiet mode (findings only, no summary)
check-init -q src/
```

Or via `python -m`:

```bash
python -m check_init src/
```

## What it detects

| Kind | Example | Flagged? |
|------|---------|----------|
| Local scalars | `int x;` | Yes |
| Pointers | `int* p;` | Yes |
| Arrays | `int arr[10];` | Yes |
| Class/struct members | `int count;` (inside class) | Only with `--members` |
| Custom types | `std::vector<int> v;` | Yes |
| CUDA qualified | `__shared__ int s[64];` | Yes |
| Function pointers | `void (*fp)(int);` | Yes |
| Initialized | `int x{};`, `int x = 0;` | No |
| Extern | `extern int x;` | No |
| For-loop vars | `for (int i = 0; ...)` | No |
| Forward declarations | `class Foo;` | No |

## Output format

Human-readable (default):

```
src/main.cpp:42:5: warning: 'count' (local) [int count;]
src/utils.h:18:3: warning: 'buffer' (array) [char buffer[256];]
```

JSON (`--json`):

```json
{
  "files_scanned": 234,
  "total_findings": 12,
  "results": [
    {
      "path": "src/main.cpp",
      "findings": [
        {
          "line": 42,
          "column": 5,
          "var_name": "count",
          "kind": "local",
          "snippet": "int count;",
          "severity": "warning"
        }
      ]
    }
  ]
}
```

## CI integration

### GitHub Actions

```yaml
- name: "Clone check-init"
  uses: actions/checkout@v4
  with:
    repository: meet-brad-ch/check_init
    path: check-init-tool

- name: "Install check-init"
  run: pip install ./check-init-tool

- name: "Scan for uninitialized variables"
  run: |
    check-init \
      --exclude third_party/ \
      --fail-on-findings \
      src/
```

## Default exclusions

The following patterns are excluded by default (override with `--exclude`):

- `third_parties/`, `third_party/`
- `build/`, `bazel-`, `cmake-build-`
- `.pb.h`, `.pb.cc` (protobuf generated)
- `generated/`

## Running tests

```bash
pip install pytest
pytest
```

## License

MIT
