import subprocess
from pathlib import Path
from typing import Dict, Any


class SandboxRunner:
    """
    Spawns and monitors an isolated Docker worker container for running
    generated Pandas ETL transformation jobs.
    """

    def __init__(
        self,
        image_name: str = "sql-agent-etl-sandbox",
        timeout_seconds: int = 60,
        memory_limit: str = "512m",
        cpu_limit: str = "1.0",
    ):
        self.image_name = image_name
        self.timeout_seconds = timeout_seconds
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

    def run_job(self, job_dir: str) -> Dict[str, Any]:
        job_path = Path(job_dir).resolve()

        input_dir = job_path / "input"
        output_dir = job_path / "output"
        script_path = job_path / "job.py"

        if not input_dir.is_dir():
            raise ValueError(f"Input directory does not exist: {input_dir}")

        if not output_dir.is_dir():
            raise ValueError(f"Output directory does not exist: {output_dir}")

        if not script_path.is_file():
            raise ValueError(f"job.py script does not exist: {script_path}")

        # Construct hardened Docker run command
        command = [
            "docker", "run", "--rm",
            "--network", "none",
            f"--cpus={self.cpu_limit}",
            f"--memory={self.memory_limit}",
            "--pids-limit=64",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
            "--mount", f"type=bind,source={input_dir},target=/workspace/input,readonly",
            "--mount", f"type=bind,source={output_dir},target=/workspace/output",
            "--mount", f"type=bind,source={script_path},target=/workspace/job.py,readonly",
            self.image_name,
            "/workspace/job.py"
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False
            )
        except FileNotFoundError:
            raise RuntimeError(
                "Docker executable not found. Please ensure Docker is installed and in your PATH."
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(
                f"ETL sandbox job exceeded execution timeout limit ({self.timeout_seconds}s)."
            ) from error

        if result.returncode != 0:
            stderr_msg = result.stderr.strip() if result.stderr else "Unknown sandbox error"
            stdout_msg = result.stdout.strip() if result.stdout else ""
            error_details = f"Exit code {result.returncode}.\nStderr: {stderr_msg[-2000:]}"
            if stdout_msg:
                error_details += f"\nStdout: {stdout_msg[-1000:]}"
            raise RuntimeError(f"Docker sandbox execution failed: {error_details}")

        return {
            "status": "success",
            "stdout": result.stdout.strip()[-4000:],
            "output_directory": str(output_dir),
        }