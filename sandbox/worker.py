

import sys
from pathlib import Path


BASE_DIR = Path("/workspace").resolve()
INPUT_DIR = (BASE_DIR / "input").resolve()
OUTPUT_DIR = (BASE_DIR / "output").resolve()


def is_inside(path: Path, parent: Path) -> bool:
    """
    Ensure a path stays inside the intended directory.
    """
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_paths() -> None:
    if not INPUT_DIR.exists():
        raise RuntimeError("Input directory does not exist.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not is_inside(INPUT_DIR, BASE_DIR):
        raise RuntimeError("Invalid input directory.")

    if not is_inside(OUTPUT_DIR, BASE_DIR):
        raise RuntimeError("Invalid output directory.")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: worker.py /workspace/job.py"
        )

    script_path = Path(sys.argv[1]).resolve()

    if not is_inside(script_path, BASE_DIR):
        raise RuntimeError(
            "The script must be inside /workspace."
        )

    if not script_path.is_file():
        raise RuntimeError("Transformation script not found.")

    validate_paths()

    # The transformation script can use these variables.
    # It should read only from INPUT_DIR and write only to OUTPUT_DIR.
    namespace = {
        "INPUT_DIR": INPUT_DIR,
        "OUTPUT_DIR": OUTPUT_DIR,
    }

    # Execute the transformation script.
    # This is still Python execution; Docker provides the
    # isolation boundary.
    exec(
        compile(
            script_path.read_text(encoding="utf-8"),
            str(script_path),
            "exec"
        ),
        {"__builtins__": __builtins__},
        namespace
    )

    print("ETL transformation completed successfully.")


if __name__ == "__main__":
    main()