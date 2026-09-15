import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.sql_guard import SQLGuard

guard = SQLGuard()

test_cases = [
    # Safe analytical queries
    ("SELECT * FROM users LIMIT 5;", True),
    ("SELECT city, COUNT(*) FROM users GROUP BY city;", True),
    ("SELECT u.id, o.amount FROM users u JOIN orders o ON u.id = o.user_id WHERE o.amount > 100;", True),
    ("SELECT city, AVG(age) FROM users WHERE age >= 18 GROUP BY city HAVING COUNT(*) > 5 ORDER BY city DESC LIMIT 10;", True),
    ("SELECT * FROM (SELECT id, name FROM customers WHERE active = true) sub WHERE id > 10;", True),
    
    # Dangerous DML operations
    ("DELETE FROM users;", False),
    ("UPDATE users SET city = 'Ahmedabad';", False),
    ("INSERT INTO users (name, city) VALUES ('John', 'Mumbai');", False),
    
    # Dangerous DDL operations
    ("DROP TABLE users;", False),
    ("CREATE TABLE test_table (id INT);", False),
    ("ALTER TABLE users ADD COLUMN is_admin BOOLEAN;", False),
    ("TRUNCATE TABLE users;", False),
    
    # Multiple statements and SQL injection patterns
    ("SELECT 1; DELETE FROM users;", False),
    ("SELECT * FROM users; DROP TABLE orders;", False),
    ("", False),
    ("   ", False),
    ("INVALID SQL STATEMENT HERE * %", False),
]


def test_sql_guard():
    passed = 0
    failed = 0

    print("================ Running SQLGuard Tests ================")
    for sql, expected in test_cases:
        result = guard.validate(sql)
        status = "PASSED" if result.is_safe == expected else "FAILED"
        if result.is_safe == expected:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] Expected Safe: {expected} | Actual Safe: {result.is_safe}")
        print(f"       SQL: {sql.strip()[:60]}")
        print(f"       Reason: {result.reason}\n")

        assert result.is_safe == expected, f"Failed on SQL: {sql}. Expected {expected}, got {result.is_safe} ({result.reason})"

    print(f"Total: {len(test_cases)} | Passed: {passed} | Failed: {failed}")
    print("================ All SQLGuard Tests Passed! ================\n")


if __name__ == "__main__":
    test_sql_guard()