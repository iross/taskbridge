"""Bartib time tracking integration for TaskBridge.

This module provides a Python interface to the bartib CLI tool for local-first time tracking.
Bartib stores all time tracking data as a plaintext log file.
"""

import subprocess


class BartibIntegration:
    """Interface to bartib CLI for time tracking operations."""

    def __init__(self, bartib_binary: str = "bartib"):
        """
        Initialize bartib integration.

        Args:
            bartib_binary: Path to bartib executable (default: "bartib" from PATH)
        """
        self.bartib_binary = bartib_binary
        self._verify_installed()

    def _verify_installed(self) -> None:
        """Verify that bartib is installed and accessible."""
        try:
            result = subprocess.run(
                [self.bartib_binary, "--version"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError(f"bartib not found or not working: {result.stderr}")
        except FileNotFoundError as e:
            raise RuntimeError(f"bartib not found at {self.bartib_binary}") from e

    def _run(self, args: list[str]) -> str:
        """Run a bartib command and return stdout output."""
        result = subprocess.run(
            [self.bartib_binary] + args,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"bartib error: {result.stderr.strip()}")
        return result.stdout

    def start_tracking(
        self,
        description: str,
        project: str,
        start_time: str | None = None,
    ) -> None:
        """
        Start tracking time for an activity.

        Args:
            description: Description of what you're working on
            project: Project name to track under
            start_time: Start time in HH:MM format (default: now)
        """
        args = ["start", "-d", description, "-p", project]
        if start_time:
            args.extend(["-t", start_time])
        self._run(args)

    def stop_tracking(self, stop_time: str | None = None) -> None:
        """
        Stop all currently running activities.

        Args:
            stop_time: Stop time in HH:MM format (default: now)
        """
        args = ["stop"]
        if stop_time:
            args.extend(["-t", stop_time])
        self._run(args)

    def list_activities(
        self,
        project: str | None = None,
        today: bool = False,
        current_week: bool = False,
        last_week: bool = False,
        from_date: str | None = None,
        to_date: str | None = None,
        number: int | None = None,
    ) -> str:
        """
        List tracked activities.

        Args:
            project: Filter by project name
            today: Show only today's activities
            current_week: Show current week's activities
            last_week: Show last week's activities
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            number: Maximum number of activities to display

        Returns:
            Formatted text output from bartib
        """
        args = ["list"]
        if today:
            args.append("--today")
        elif current_week:
            args.append("--current_week")
        elif last_week:
            args.append("--last_week")
        if from_date:
            args.extend(["--from", from_date])
        if to_date:
            args.extend(["--to", to_date])
        if project:
            args.extend(["-p", project])
        if number is not None:
            args.extend(["-n", str(number)])
        return self._run(args)

    def get_report(
        self,
        project: str | None = None,
        today: bool = False,
        current_week: bool = False,
        last_week: bool = False,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> str:
        """
        Get a time report summarizing tracked activities.

        Args:
            project: Filter by project name
            today: Report on today's activities
            current_week: Report on current week
            last_week: Report on last week
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            Formatted report text from bartib
        """
        args = ["report"]
        if today:
            args.append("--today")
        elif current_week:
            args.append("--current_week")
        elif last_week:
            args.append("--last_week")
        if from_date:
            args.extend(["--from", from_date])
        if to_date:
            args.extend(["--to", to_date])
        if project:
            args.extend(["-p", project])
        return self._run(args)

    def get_current(self) -> str:
        """
        Show currently running activities.

        Returns:
            Text output showing active activities, empty if none running
        """
        return self._run(["current"])
