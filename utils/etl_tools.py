import os
import shutil
import uuid
import urllib.request
import json
from pathlib import Path
from typing import Dict, Any, Optional

import pandas as pd

from utils.sandbox_runner import SandboxRunner
from utils.python_guard import PythonGuard


class ETLSandboxService:
    """
    Manages isolated workspace directories and executes Pandas transformation
    scripts inside the secure Docker sandbox.
    """

    def __init__(self, workspace: str = "raw_data/jobs"):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.runner = SandboxRunner(
            image_name="sql-agent-etl-sandbox",
            timeout_seconds=60,
            memory_limit="512m",
            cpu_limit="1.0",
        )

    def execute_pandas_code(
        self,
        generated_code: str,
        input_file: str,
        output_folder: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sets up the isolated job directory, writes job.py, executes inside
        the Docker container, validates outputs, and copies results to output_folder.
        """
        source_file = Path(input_file).resolve()
        if not source_file.is_file():
            raise ValueError(f"Input file does not exist: {input_file}")

        job_id = uuid.uuid4().hex
        job_dir = self.workspace / f"job_{job_id}"

        input_dir = job_dir / "input"
        output_dir = job_dir / "output"

        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Copy only the designated input file into the isolated input directory
            destination_file = input_dir / source_file.name
            shutil.copy2(source_file, destination_file)

            # Write the generated code to job.py
            script_path = job_dir / "job.py"
            script_path.write_text(generated_code, encoding="utf-8")

            # Execute via Docker SandboxRunner
            result = self.runner.run_job(str(job_dir))

            # Validate that output files were produced
            output_files = list(output_dir.glob("*"))
            if not output_files:
                raise RuntimeError(
                    "Sandbox completed successfully but produced no output files in OUTPUT_DIR."
                )

            # Post-execution output validation & publishing
            published_files = []
            if output_folder:
                dest_dir = Path(output_folder).resolve()
                dest_dir.mkdir(parents=True, exist_ok=True)

                for out_file in output_files:
                    if out_file.is_file() and out_file.stat().st_size > 0:
                        # Verify file is readable / valid format
                        self._validate_output_file(out_file)
                        dest_file = dest_dir / out_file.name
                        shutil.copy2(out_file, dest_file)
                        published_files.append(str(dest_file))
                    else:
                        raise RuntimeError(f"Output file {out_file.name} is empty (0 bytes).")

            return {
                "job_id": job_id,
                "status": result["status"],
                "stdout": result["stdout"],
                "output_directory": str(output_dir),
                "published_files": published_files,
            }

        finally:
            # Clean up temporary sandbox job directory
            shutil.rmtree(job_dir, ignore_errors=True)

    def _validate_output_file(self, file_path: Path) -> None:
        """Verify the output dataset format and integrity."""
        suffix = file_path.suffix.lower()
        try:
            if suffix == ".csv":
                df = pd.read_csv(file_path, nrows=5)
            elif suffix == ".json":
                df = pd.read_json(file_path)
            elif suffix in [".parquet", ".pq"]:
                df = pd.read_parquet(file_path)
            else:
                return  # Custom format, passed byte check
            if df.empty and file_path.stat().st_size == 0:
                raise ValueError("Dataset is empty.")
        except Exception as e:
            raise RuntimeError(f"Output data validation failed for {file_path.name}: {e}") from e


class ETLTools:
    """
    Core ETL operations utility integrating API extraction, preview context generation,
    AST code validation with PythonGuard, and isolated execution via ETLSandboxService.
    """

    def __init__(self, workspace: str = "raw_data/jobs"):
        self.python_guard = PythonGuard()
        self.sandbox_service = ETLSandboxService(workspace=workspace)

    def extract_load(self, url: str, output_folder: str, format: str = "csv") -> str:
        """
        Extract data from an API endpoint URL and save it to output_folder
        in the requested format (csv, json, parquet).
        """
        try:
            dest_dir = Path(output_folder).resolve()
            dest_dir.mkdir(parents=True, exist_ok=True)

            # Fetch data from API
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "SQL-AGENT-ETL/1.0"}
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                raw_bytes = response.read()
                raw_json = json.loads(raw_bytes.decode("utf-8"))

            # Normalize JSON data to Pandas DataFrame
            if isinstance(raw_json, dict):
                if "results" in raw_json and isinstance(raw_json["results"], list):
                    df = pd.json_normalize(raw_json["results"])
                else:
                    # Single record with possible nested structures
                    flat_record = {}
                    for k, v in raw_json.items():
                        if isinstance(v, (dict, list)):
                            flat_record[k] = json.dumps(v)
                        else:
                            flat_record[k] = v
                    df = pd.DataFrame([flat_record])
            elif isinstance(raw_json, list):
                df = pd.json_normalize(raw_json)
            else:
                df = pd.DataFrame([{"data": raw_json}])

            # Save in requested format
            norm_format = format.lower().strip()
            out_filename = f"extracted_data.{norm_format}"
            out_path = dest_dir / out_filename

            if norm_format == "csv":
                df.to_csv(out_path, index=False)
            elif norm_format == "json":
                df.to_json(out_path, orient="records", indent=2)
            elif norm_format == "parquet":
                df.to_parquet(out_path, index=False)
            else:
                # Default to CSV
                out_path = dest_dir / "extracted_data.csv"
                df.to_csv(out_path, index=False)

            return f"Successfully extracted data from '{url}' and saved {len(df)} rows to '{out_path}'."

        except Exception as e:
            error_msg = f"Failed to extract and load data from '{url}': {e}"
            print(error_msg)
            return error_msg

    def transform_load_context(self, input_file_path: str) -> str:
        """
        Read top sample rows from input_file_path to generate schema context for LLM.
        """
        try:
            file_path = Path(input_file_path).resolve()
            if not file_path.is_file():
                return f"Input file not found at path: {input_file_path}"

            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                df = pd.read_csv(file_path, nrows=5)
            elif suffix == ".json":
                df = pd.read_json(file_path)
                df = df.head(5)
            elif suffix in [".parquet", ".pq"]:
                df = pd.read_parquet(file_path)
                df = df.head(5)
            else:
                return f"Unsupported file format '{suffix}' for context preview."

            columns_info = [f"{col} ({dtype})" for col, dtype in zip(df.columns, df.dtypes)]
            context_str = f"Columns & Types: {', '.join(columns_info)}\nSample Rows:\n{df.to_string(index=False)}"
            return context_str

        except Exception as e:
            return f"Error reading context from {input_file_path}: {e}"

    def execute_code(
        self,
        pandas_code: str,
        input_file_path: str,
        output_folder: str,
        output_format: str = "csv"
    ) -> str:
        """
        Validate generated Pandas code with PythonGuard AST checker,
        then run safely inside Docker sandbox.
        """
        # Step 1: Pre-execution AST validation
        validation = self.python_guard.validate(pandas_code)
        if not validation.is_safe:
            return f"Transformation rejected by Python AST Guard: {validation.reason}"

        # Step 2: Execute in Docker Sandbox
        try:
            exec_result = self.sandbox_service.execute_pandas_code(
                generated_code=pandas_code,
                input_file=input_file_path,
                output_folder=output_folder,
            )
            published = exec_result.get("published_files", [])
            published_str = ", ".join(published) if published else output_folder
            return f"Sandbox execution successful. Output published to: {published_str}"

        except Exception as e:
            return f"Sandbox transformation failed: {e}"