from dataclasses import dataclass, field


@dataclass
class Finding:
    file: str
    line: int
    column: int
    var_name: str
    kind: str  # "local", "member", "array", "pointer"
    snippet: str
    severity: str = "warning"

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}: {self.severity}: '{self.var_name}' ({self.kind}) is not initialized"


@dataclass
class FileResult:
    path: str
    findings: list = field(default_factory=list)
    parse_errors: list = field(default_factory=list)
