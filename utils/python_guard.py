import ast
from dataclasses import dataclass


@dataclass
class PythonValidationResult:
    is_safe: bool
    reason: str


class PythonGuard(ast.NodeVisitor):
    """
    Deterministic AST visitor that checks generated Python transformation scripts
    for forbidden imports, dangerous builtins, or suspicious calls before execution.
    """

    # Imports that are not required for pure Pandas/PyArrow data transformations
    FORBIDDEN_IMPORTS = {
        "os",
        "subprocess",
        "socket",
        "shutil",
        "sys",
        "ctypes",
        "pathlib",
        "requests",
        "urllib",
        "http",
        "ftplib",
        "pickle",
        "shelve",
        "multiprocessing",
        "threading",
        "pty",
        "posix",
        "posixpath",
        "builtins",
        "importlib",
    }

    FORBIDDEN_CALLS = {
        "exec",
        "eval",
        "compile",
        "__import__",
        "breakpoint",
        "globals",
        "locals",
    }

    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            root_name = alias.name.split(".")[0]
            if root_name in self.FORBIDDEN_IMPORTS:
                self.errors.append(f"Forbidden import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            root_name = node.module.split(".")[0]
            if root_name in self.FORBIDDEN_IMPORTS:
                self.errors.append(f"Forbidden import from: '{node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_CALLS:
                self.errors.append(f"Forbidden function call: '{node.func.id}()'")
        self.generic_visit(node)

    def validate(self, code: str) -> PythonValidationResult:
        if not code or not code.strip():
            return PythonValidationResult(
                is_safe=False,
                reason="Python transformation code is empty."
            )

        try:
            tree = ast.parse(code)
        except SyntaxError as error:
            return PythonValidationResult(
                is_safe=False,
                reason=f"Python syntax error: {error}"
            )

        self.errors = []
        self.visit(tree)

        if self.errors:
            return PythonValidationResult(
                is_safe=False,
                reason="; ".join(self.errors)
            )

        return PythonValidationResult(
            is_safe=True,
            reason="Python code passed the static AST validation checks."
        )
