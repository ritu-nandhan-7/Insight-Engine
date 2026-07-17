"""Constants for the code validator package."""

from __future__ import annotations

FORBIDDEN_IMPORT_MODULES = {
    "os",
    "subprocess",
    "socket",
    "requests",
    "pathlib",
    "shutil",
    "sys",
    "builtins",
}

FORBIDDEN_FUNCTIONS = {
    "eval",
    "exec",
    "compile",
    "open",
    "input",
    "__import__",
}

REQUIRED_OUTPUT_VARIABLE = "fig"