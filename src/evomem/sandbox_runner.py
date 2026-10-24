"""OpenHands terminal adapter that confines repository commands to Docker."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .execution import DockerWorkspaceExecutor


class DockerTerminalExecutor:
    """Adapter loaded only when the optional OpenHands packages are installed."""
    is_pooled = False

    def __init__(self, repository: str | Path, image: str, *, timeout_seconds: int = 120):
        self._docker = DockerWorkspaceExecutor(str(Path(repository).resolve()), image)
        self._timeout_seconds = timeout_seconds
        self.working_dir = "/workspace"
        self._active: subprocess.Popen[str] | None = None

    def __call__(self, action: Any, conversation: Any = None) -> Any:
        from openhands.tools.terminal.definition import TerminalObservation

        if action.reset:
            return TerminalObservation.from_text("Docker terminal state reset; commands do not persist shell state.", command="[RESET]", exit_code=0)
        if action.is_input:
            return TerminalObservation.from_text("Interactive terminal input is unavailable in the Docker sandbox.", is_error=True, command=action.command, exit_code=None)
        available, reason = self._docker.availability()
        if not available:
            return TerminalObservation.from_text(reason, is_error=True, command=action.command, exit_code=None)
        timeout = min(float(action.timeout or self._timeout_seconds), float(self._timeout_seconds))
        command = self._docker.docker_command(["/bin/sh", "-lc", action.command])
        try:
            completed = subprocess.run(command, text=True, capture_output=True, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or "") + (exc.stderr or "")
            return TerminalObservation.from_text(output or f"Command exceeded {timeout:g} seconds.", is_error=True, command=action.command, exit_code=-1, timeout=True)
        output = (completed.stdout or "") + (completed.stderr or "")
        return TerminalObservation.from_text(output, is_error=completed.returncode != 0, command=action.command, exit_code=completed.returncode)

    def interrupt(self) -> None:
        if self._active is not None:
            self._active.terminate()

    def close(self) -> None:
        self.interrupt()
