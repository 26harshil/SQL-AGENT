from dataclasses import dataclass
from typing import Optional

import sqlglot
from sqlglot import exp

# sqlglot: Parses SQL into an abstract syntax tree (AST).
# AST=An Abstract Syntax Tree represents SQL as structured objects rather than plain text.
# SELECT city, COUNT(*)
# FROM users
# GROUP BY city;
# Conceptually, the parser produces a structure similar to:
# SELECT
#  ├── Column(city)
#  ├── COUNT(*)
#  ├── FROM users
#  └── GROUP BY city


# dataclass is a Python feature that automatically generates useful methods for classes, such as __init__().
# instead of this you can write below code
# class SQLValidationResult:
#     def __init__(self, is_safe, reason, normalized_sql=None):
#         self.is_safe = is_safe
#         self.reason = reason
#         self.normalized_sql = normalized_sql
@dataclass
class SQLValidationResult:
    is_safe: bool
    reason: str
    normalized_sql: Optional[str] = None


class SQLGuard:
    """
    Deterministic guard for read-only PostgreSQL analytics queries.

    This is a policy layer, not a replacement for database permissions.
    """

    FORBIDDEN_EXPRESSIONS = (
        exp.Insert,
        exp.Update,
        exp.Delete,
        exp.Drop,
        exp.Alter,
        exp.Create,
        exp.TruncateTable,
    )

    def validate(self, query: str) -> SQLValidationResult:
        if not query or not query.strip():
            return SQLValidationResult(is_safe=False, reason="SQL query is empty.")
        query = query.strip()

        try:
            # Parse all statements, not only the first one.
            statement = sqlglot.parse(query, read="postgres")
        except sqlglot.errors.ParseError as e:
            return SQLValidationResult(
                is_safe=False, reason=f"SQL parse error: {str(e)}"
            )

        if not statement:
            return SQLValidationResult(
                is_safe=False, reason="No valid SQL statements found."
            )
        # For a basic analytics agent, permit exactly one statement.
        if len(statement) != 1:
            return SQLValidationResult(
                is_safe=False, reason="Multiple SQL statements are not allowed."
            )
        statement = statement[0]

        if not isinstance(statement, exp.Select):
            return SQLValidationResult(
                is_safe=False,
                reason=(
                    "Only SELECT statements are permitted. "
                    f"Detected: {type(statement).__name__}"
                ),
            )

        # Defense in depth: reject dangerous expressions anywhere
        # in the parsed AST.
        for node in statement.walk():
            # statement.walk() = Traverses the parsed expression tree.
            if isinstance(node, self.FORBIDDEN_EXPRESSIONS):
                return SQLValidationResult(
                    is_safe=False,
                    reason=(
                        "Forbidden SQL operation detected: " f"{type(node).__name__}"
                    ),
                )
        normalized_sql = statement.sql(dialect="postgres")

        return SQLValidationResult(
            is_safe=True,
            reason="SQL query is safe and permitted.",
            normalized_sql=normalized_sql,
        )
