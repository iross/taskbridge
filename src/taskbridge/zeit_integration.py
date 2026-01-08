"""
Zeit time tracking integration for TaskBridge.

This module provides a Python interface to the zeit CLI tool for local-first time tracking.
Zeit stores all time tracking data locally and can be integrated with task management systems.
"""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class TimeBlock:
    """Represents a zeit time tracking block."""

    key: str
    project_sid: str
    task_sid: str
    note: str
    start: str
    end: str
    duration: int

    @classmethod
    def from_dict(cls, data: dict) -> "TimeBlock":
        """Create TimeBlock from zeit JSON output."""
        return cls(
            key=data["key"],
            project_sid=data["project_sid"],
            task_sid=data["task_sid"],
            note=data["note"],
            start=data["start"],
            end=data["end"],
            duration=data["duration"],
        )


@dataclass
class ZeitProject:
    """Represents a zeit project."""

    sid: str
    display_name: str
    color: str
    total_blocks: int
    total_amount: int
    tasks: list[dict]

    @classmethod
    def from_dict(cls, data: dict) -> "ZeitProject":
        """Create ZeitProject from zeit JSON output."""
        return cls(
            sid=data["sid"],
            display_name=data["display_name"],
            color=data["color"],
            total_blocks=data["total_blocks"],
            total_amount=data["total_amount"],
            tasks=data.get("tasks", []) or [],
        )


class ZeitIntegration:
    """Interface to zeit CLI for time tracking operations."""

    def __init__(self, zeit_binary: str = "zeit"):
        """
        Initialize zeit integration.

        Args:
            zeit_binary: Path to zeit executable (default: "zeit" from PATH)
        """
        self.zeit_binary = zeit_binary
        self._verify_zeit_installed()

    def _verify_zeit_installed(self) -> None:
        """Verify that zeit is installed and accessible."""
        try:
            result = subprocess.run(
                [self.zeit_binary, "version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(f"zeit not found or not working: {result.stderr}")
        except FileNotFoundError as e:
            raise RuntimeError(f"zeit not found at {self.zeit_binary}") from e

    def _run_zeit_command(
        self, args: list[str], check: bool = True, expect_json: bool = True
    ) -> dict | list | None:
        """
        Run a zeit command and return JSON output.

        Args:
            args: Command arguments (e.g., ["start", "work", "-p", "myproject"])
            check: Whether to raise exception on non-zero exit code
            expect_json: Whether to expect JSON output (some commands return plain text)

        Returns:
            Parsed JSON output from zeit, or None if command produces no JSON
        """
        # Always request JSON output
        full_args = [self.zeit_binary, "-f", "json"] + args

        result = subprocess.run(
            full_args,
            capture_output=True,
            text=True,
            check=check,
        )

        if not result.stdout.strip():
            return None

        # Some zeit commands don't support JSON output and return plain text
        if not expect_json:
            return {"success": True, "message": result.stdout.strip()}

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            # If JSON parsing fails but we expected JSON, it might be a plain text response
            # This can happen with some zeit commands like "block edit"
            return {"success": True, "message": result.stdout.strip()}

    # ============================================================================
    # Time Tracking Operations (Start/Stop)
    # ============================================================================

    def start_tracking(
        self,
        note: str,
        project: str | None = None,
        task: str | None = None,
        start_time: str | None = None,
    ) -> dict[str, Any]:
        """
        Start tracking time for an activity.

        Args:
            note: Description of what you're working on
            project: Project SID (simplified ID)
            task: Task SID
            start_time: Start timestamp (default: now)

        Returns:
            dict: Zeit response with tracking information

        Example:
            >>> zeit.start_tracking("Working on authentication", project="taskbridge",
            task="auth")
        """
        args = ["start"]

        if note:
            args.extend(["-n", note])
        if project:
            args.extend(["-p", project])
        if task:
            args.extend(["-t", task])
        if start_time:
            args.extend(["-s", start_time])

        result = self._run_zeit_command(args)
        if isinstance(result, dict):
            return result
        return {}

    def stop_tracking(self, note: str | None = None, end_time: str | None = None) -> dict[str, Any]:
        """
        Stop the current time tracking session.

        Args:
            note: Optional note to add when stopping
            end_time: End timestamp (default: now)

        Returns:
            dict: Zeit response with stopped tracking information

        Example:
            >>> zeit.stop_tracking("Completed authentication module")
        """
        args = ["end"]

        if note:
            args.extend(["-n", note])
        if end_time:
            args.extend(["-e", end_time])

        result = self._run_zeit_command(args)
        if isinstance(result, dict):
            return result
        return {}

    # ============================================================================
    # CRUD Operations for Time Blocks
    # ============================================================================

    def list_blocks(
        self,
        project: str | None = None,
        task: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> list[TimeBlock]:
        """
        List time tracking blocks with optional filters.

        Args:
            project: Filter by project SID
            task: Filter by task SID
            start: Start timestamp filter
            end: End timestamp filter

        Returns:
            list[TimeBlock]: List of time blocks

        Example:
            >>> blocks = zeit.list_blocks(project="taskbridge", start="today")
            >>> for block in blocks:
            ...     print(f"{block.note}: {block.start} -> {block.end}")
        """
        args = ["block"]

        if project:
            args.extend(["-p", project])
        if task:
            args.extend(["-t", task])
        if start:
            args.extend(["-s", start])
        if end:
            args.extend(["-e", end])

        result = self._run_zeit_command(args)
        if not result:
            return []

        return [TimeBlock.from_dict(block) for block in result]

    def get_block(self, block_key: str) -> TimeBlock | None:
        """
        Get a specific time block by its key.

        Args:
            block_key: The block key (UUID format)

        Returns:
            TimeBlock or None if not found

        Example:
            >>> block = zeit.get_block("block:019b93cf-e041-714c-9cd3-832d90bab3d2")
        """
        args = ["block", block_key]

        result = self._run_zeit_command(args, check=False)
        if not result:
            return None

        # zeit returns a list even for a single block query
        if isinstance(result, list):
            if not result:
                return None
            result = result[0]

        return TimeBlock.from_dict(result)

    def edit_block(
        self,
        block_key: str,
        note: str | None = None,
        project: str | None = None,
        task: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        """
        Edit an existing time block.

        Args:
            block_key: The block key to edit
            note: New note/description
            project: New project SID
            task: New task SID
            start: New start timestamp
            end: New end timestamp

        Returns:
            dict: Zeit response

        Example:
            >>> zeit.edit_block("block:019b93cf...", note="Updated description")
        """
        args = ["block", "edit", block_key]

        if note:
            args.extend(["-n", note])
        if project:
            args.extend(["-p", project])
        if task:
            args.extend(["-t", task])
        if start:
            args.extend(["-s", start])
        if end:
            args.extend(["-e", end])

        result = self._run_zeit_command(args)
        if isinstance(result, dict):
            return result
        return {}

    # ============================================================================
    # Project Management
    # ============================================================================

    def list_projects(self) -> list[ZeitProject]:
        """
        List all zeit projects with their tasks and statistics.

        Returns:
            list[ZeitProject]: List of projects

        Example:
            >>> projects = zeit.list_projects()
            >>> for proj in projects:
            ...     print(f"{proj.display_name}: {proj.total_blocks} blocks")
        """
        result = self._run_zeit_command(["project"])
        if not result:
            return []

        return [ZeitProject.from_dict(proj) for proj in result]

    def get_project(self, project_sid: str) -> ZeitProject | None:
        """
        Get a specific project by its SID.

        Args:
            project_sid: Project simplified ID

        Returns:
            ZeitProject or None if not found

        Example:
            >>> project = zeit.get_project("taskbridge")
        """
        projects = self.list_projects()
        for proj in projects:
            if proj.sid == project_sid:
                return proj
        return None

    # ============================================================================
    # Statistics & Reporting
    # ============================================================================

    def get_stats(
        self,
        project: str | None = None,
        task: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> dict[str, Any]:
        """
        Get time tracking statistics.

        Args:
            project: Filter by project SID
            task: Filter by task SID
            start: Start timestamp
            end: End timestamp

        Returns:
            dict: Statistics from zeit

        Example:
            >>> stats = zeit.get_stats(project="taskbridge", start="this week")
        """
        args = ["stat"]

        if project:
            args.extend(["-p", project])
        if task:
            args.extend(["-t", task])
        if start:
            args.extend(["-s", start])
        if end:
            args.extend(["-e", end])

        result = self._run_zeit_command(args)
        if isinstance(result, dict):
            return result
        return {}

    # ============================================================================
    # Export Operations
    # ============================================================================

    def export_data(
        self,
        output_file: Path | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> str:
        """
        Export zeit data (useful for backups or migration).

        Args:
            output_file: Optional file to write export to
            start: Start timestamp
            end: End timestamp

        Returns:
            str: Exported data as string

        Example:
            >>> data = zeit.export_data(output_file=Path("zeit_backup.json"))
        """
        args = ["export"]

        if start:
            args.extend(["-s", start])
        if end:
            args.extend(["-e", end])

        # For export, we want the raw output
        result = subprocess.run(
            [self.zeit_binary] + args,
            capture_output=True,
            text=True,
            check=True,
        )

        if output_file:
            output_file.write_text(result.stdout)

        return result.stdout
