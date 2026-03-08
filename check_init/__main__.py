"""CLI entry point for check_init — detect uninitialized C/C++/CUDA variable declarations."""

import argparse
import json
import os
import sys
from pathlib import Path

from .config import DEFAULT_EXCLUDES, DEFAULT_EXTENSIONS
from .scanner import scan_file
from .types import FileResult


def find_files(
    paths: list,
    extensions: set,
    excludes: list,
) -> list:
    """Find all source files under the given paths."""
    files = []
    for path_str in paths:
        path = Path(path_str)
        if path.is_file():
            if path.suffix in extensions:
                files.append(str(path))
            continue
        for root, dirs, filenames in os.walk(path):
            # Filter excluded directories in-place
            dirs[:] = [
                d
                for d in dirs
                if not any(excl.rstrip("/") == d or root.startswith(excl) for excl in excludes)
            ]
            for fname in filenames:
                fpath = os.path.join(root, fname)
                # Check extension
                _, ext = os.path.splitext(fname)
                if ext not in extensions:
                    continue
                # Check file-level excludes
                if any(excl in fpath for excl in excludes):
                    continue
                files.append(fpath)
    return sorted(files)


def main():
    parser = argparse.ArgumentParser(
        prog="check_init",
        description="Detect uninitialized C/C++/CUDA variable declarations.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Files or directories to scan",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude files/dirs matching pattern (repeatable)",
    )
    parser.add_argument(
        "--include-ext",
        default=None,
        help="Comma-separated file extensions to scan (default: .cpp,.cc,.h,.hpp,.cu,.cuh,.c,.cxx,.hxx)",
    )
    parser.add_argument(
        "--members",
        action="store_true",
        help="Also check class/struct member declarations",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="output_json",
        help="Output as JSON",
    )
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="Exit with code 1 if findings exist",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Only output findings, no summary",
    )

    args = parser.parse_args()

    # Build extension set
    if args.include_ext:
        extensions = set()
        for ext in args.include_ext.split(","):
            ext = ext.strip()
            if not ext.startswith("."):
                ext = "." + ext
            extensions.add(ext)
    else:
        extensions = DEFAULT_EXTENSIONS

    # Build exclude list
    excludes = DEFAULT_EXCLUDES + args.exclude

    # Find files
    files = find_files(args.paths, extensions, excludes)

    if not files and not args.quiet:
        print("No matching files found.", file=sys.stderr)
        sys.exit(0)

    # Scan files
    all_results: list[FileResult] = []
    total_findings = 0

    for fpath in files:
        try:
            with open(fpath, "r", errors="replace") as f:
                source = f.read()
        except OSError as e:
            if not args.quiet:
                print(f"Error reading {fpath}: {e}", file=sys.stderr)
            continue

        result = scan_file(source, filepath=fpath, check_members=args.members)
        if result.findings:
            all_results.append(result)
            total_findings += len(result.findings)

    # Output
    if args.output_json:
        output = {
            "files_scanned": len(files),
            "total_findings": total_findings,
            "results": [
                {
                    "path": r.path,
                    "findings": [
                        {
                            "line": f.line,
                            "column": f.column,
                            "var_name": f.var_name,
                            "kind": f.kind,
                            "snippet": f.snippet,
                            "severity": f.severity,
                        }
                        for f in r.findings
                    ],
                }
                for r in all_results
            ],
        }
        print(json.dumps(output, indent=2))
    else:
        for r in all_results:
            for f in r.findings:
                print(
                    f"{r.path}:{f.line}:{f.column}: warning: '{f.var_name}' ({f.kind}) [{f.snippet}]"
                )

        if not args.quiet:
            print(
                f"\n{total_findings} finding(s) in {len(all_results)} file(s) "
                f"({len(files)} files scanned)",
                file=sys.stderr,
            )

    if args.fail_on_findings and total_findings > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
