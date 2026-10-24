"""Execution policy; intentionally not a pretend sandbox."""
from __future__ import annotations

from dataclasses import dataclass
import os
import shutil
import subprocess
from typing import Sequence


@dataclass(frozen=True)
class ExecutionResult:
    status: str
    reason: str
    command: list[str] | None = None
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


class IsolatedExecutor:
    """Contract for a container/VM executor supplied by an integration."""
    def run(self, command: Sequence[str], *, timeout_seconds: int) -> ExecutionResult:  # pragma: no cover - interface
        raise NotImplementedError


class DockerExecutor(IsolatedExecutor):
    """Docker boundary with no network, dropped capabilities, and read-only repo mount."""
    def __init__(self, repository_root: str, image: str, *, memory: str = "2g", cpus: str = "2", pids_limit: int = 256):
        self.repository_root, self.image = repository_root, image
        self.memory, self.cpus, self.pids_limit = memory, cpus, pids_limit

    @staticmethod
    def availability() -> tuple[bool, str]:
        if shutil.which("docker") is None:
            return False, "Docker CLI was not found on PATH."
        try:
            probe = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], text=True, capture_output=True, timeout=5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return False, "Docker daemon probe timed out or could not start."
        if probe.returncode == 0 and probe.stdout.strip():
            return True, "Docker daemon is reachable."
        detail = (probe.stderr or probe.stdout or "no response").strip().replace("\n", " ")
        return False, f"Docker daemon probe failed: {detail}"

    @staticmethod
    def available() -> bool:
        return DockerExecutor.availability()[0]

    def docker_command(self, command: Sequence[str]) -> list[str]:
        return ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--pids-limit", str(self.pids_limit), "--memory", self.memory, "--cpus", self.cpus, "--tmpfs", "/tmp:rw,noexec,nosuid,size=512m",
                "--mount", f"type=bind,src={self.repository_root},dst=/workspace,readonly", "--workdir", "/workspace", self.image, *command]

    def run(self, command: Sequence[str], *, timeout_seconds: int) -> ExecutionResult:
        available, reason = self.availability()
        if not available:
            return ExecutionResult("skipped", f"{reason} Command was not run.", list(command))
        try:
            completed = subprocess.run(self.docker_command(command), text=True, capture_output=True, timeout=timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult("timeout", f"Docker command exceeded {timeout_seconds} seconds.", list(command), stdout=exc.stdout or "", stderr=exc.stderr or "")
        return ExecutionResult("completed" if completed.returncode == 0 else "failed", "Executed in constrained Docker container.", list(command), completed.returncode, completed.stdout, completed.stderr)


class DockerWorkspaceExecutor(DockerExecutor):
    """A writable-workspace Docker boundary for an agent's terminal tool.

    Model calls remain outside this executor. The container has no network and
    sees only the supplied disposable repository at ``/workspace``.
    """
    def docker_command(self, command: Sequence[str]) -> list[str]:
        root = os.path.abspath(self.repository_root)
        return ["docker", "run", "--rm", "--network", "none", "--read-only", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "--pids-limit", str(self.pids_limit), "--memory", self.memory, "--cpus", self.cpus, "--tmpfs", "/tmp:rw,noexec,nosuid,size=512m",
                "--mount", f"type=bind,src={root},dst=/workspace", "--workdir", "/workspace", self.image, *command]


def execute_if_isolated(command: Sequence[str], executor: IsolatedExecutor | None, timeout_seconds: int = 30) -> ExecutionResult:
    if executor is None:
        return ExecutionResult("skipped", "No isolated executor is configured; command was not run.", list(command))
    if not command:
        return ExecutionResult("rejected", "Empty command.")
    return executor.run(command, timeout_seconds=timeout_seconds)
