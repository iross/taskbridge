"""Configuration management for TaskBridge."""

import os
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

import requests
import typer
import yaml


class Config:
    """Configuration management for TaskBridge."""

    def __init__(self):
        self.config_dir = Path.home() / ".taskbridge"
        self.config_file = self.config_dir / "config.yaml"
        self._config_data: dict[str, Any] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    self._config_data = yaml.safe_load(f) or {}
            except Exception as e:
                typer.echo(f"Error loading config: {e}")
                self._config_data = {}
        else:
            self._config_data = {}

    def _save_config(self) -> None:
        """Save configuration to file."""
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(exist_ok=True)

        try:
            with open(self.config_file, "w") as f:
                yaml.safe_dump(self._config_data, f, default_flow_style=False)
        except Exception as e:
            typer.echo(f"Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config_data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config_data[key] = value
        self._save_config()

    def get_todoist_token(self) -> str | None:
        """Get Todoist API token."""
        return self.get("todoist_token")

    def get_todoist_sync_label(self) -> str:
        """Get Todoist sync label for automatic note creation."""
        return self.get("todoist_sync_label", "@obsidian")

    def get_meetings(self) -> dict[str, dict]:
        """Get all defined recurring meeting templates.

        Returns:
            Dict mapping alias to {description, project, client, tags}
        """
        return self.get("meetings", {})

    def set_meeting(
        self,
        alias: str,
        description: str,
        project: str = "",
        client: str = "",
        tags: list[str] | None = None,
    ) -> None:
        """Define or update a recurring meeting template."""
        meetings = self.get_meetings()
        meetings[alias] = {
            "description": description,
            "project": project,
            "client": client,
            "tags": tags or [],
        }
        self.set("meetings", meetings)

    def delete_meeting(self, alias: str) -> bool:
        """Remove a recurring meeting definition. Returns False if alias not found."""
        meetings = self.get_meetings()
        if alias not in meetings:
            return False
        del meetings[alias]
        self.set("meetings", meetings)
        return True

    def get_todoist_project_mappings(self) -> dict[str, dict[str, str]]:
        """Get Todoist project to Obsidian folder mappings.

        Returns:
            Dict mapping project IDs to {client: str, folder: str}
        """
        return self.get("todoist_project_mappings", {})

    def set_todoist_project_mapping(self, project_id: str, client: str, folder: str) -> None:
        """Set mapping for a Todoist project to Obsidian folder."""
        mappings = self.get_todoist_project_mappings()
        mappings[project_id] = {"client": client, "folder": folder}
        self.set("todoist_project_mappings", mappings)

    def validate_todoist_token(self, token: str) -> bool:
        """Validate Todoist API token."""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                "https://api.todoist.com/rest/v2/projects", headers=headers, timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def get_obsidian_vault_path(self) -> str | os.PathLike[str]:
        """Get Obsidian vault path."""
        return self.get("obsidian_vault_path")

    def get_obsidian_vault_name(self) -> str | None:
        """Get Obsidian vault name."""
        return self.get("obsidian_vault_name", "obsidian")

    def set_obsidian_config(self, vault_path: str, vault_name: str = "obsidian") -> None:
        """Set Obsidian vault configuration."""
        # Validate the vault path exists
        vault_path_obj = Path(vault_path).expanduser()
        if not vault_path_obj.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")
        if not vault_path_obj.is_dir():
            raise ValueError(f"Vault path is not a directory: {vault_path}")

        self.set("obsidian_vault_path", str(vault_path_obj))
        self.set("obsidian_vault_name", vault_name)

    def get_obsidian_projects(self) -> list[str]:
        """Get list of existing Obsidian projects by scanning the vault."""
        vault_path = self.get_obsidian_vault_path()
        if not vault_path:
            return []

        projects_dir = Path(vault_path) / "10 Projects"
        if not projects_dir.exists():
            return []

        # Get all subdirectories (excluding hidden ones)
        projects = []
        for item in projects_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                projects.append(item.name)

        return sorted(projects)

    def archive_obsidian_project(self, project_name: str) -> bool:
        """Archive an Obsidian project by moving it to the Archive directory."""
        vault_path = self.get_obsidian_vault_path()
        if not vault_path:
            raise ValueError("Obsidian vault path not configured")

        projects_dir = Path(vault_path) / "10 Projects"
        archive_dir = Path(vault_path) / "40 Archive"

        source_path = projects_dir / project_name
        dest_path = archive_dir / project_name

        # Check if source exists
        if not source_path.exists():
            raise ValueError(f"Project '{project_name}' does not exist")

        if not source_path.is_dir():
            raise ValueError(f"'{project_name}' is not a directory")

        # Create archive directory if it doesn't exist
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Check if destination already exists
        if dest_path.exists():
            raise ValueError(f"Project '{project_name}' already exists in archive")

        # Move the directory
        import shutil

        shutil.move(str(source_path), str(dest_path))

        return True

    def create_project_directory(self, project_name: str) -> Path:
        """Create a project directory in the Obsidian vault."""
        vault_path = self.get_obsidian_vault_path()
        if not vault_path:
            raise ValueError("Obsidian vault path not configured")

        projects_dir = Path(vault_path) / "10 Projects"
        project_dir = projects_dir / project_name

        # Create directories if they don't exist
        project_dir.mkdir(parents=True, exist_ok=True)

        return project_dir

    def create_task_note(
        self,
        project_name: str,
        task_title: str,
        client: str = "",
        status: str = "backlog",
        tags: list | None = None,
    ) -> Path:
        """Create a task-specific note with frontmatter."""
        if tags is None:
            tags = []

        project_dir = self.create_project_directory(project_name)

        # Sanitize filename
        safe_title = "".join(c for c in task_title if c.isalnum() or c in (" ", "-", "_")).rstrip()
        note_path = project_dir / f"{safe_title}.md"

        # Create frontmatter
        frontmatter = {
            "fileClass": "task",
            "project": project_name,
            "status": status,
            "client": client,
            "tags": tags,
            "due": "",
        }

        # Only create the note if it doesn't already exist
        if not note_path.exists():
            # Write the note with frontmatter
            with open(note_path, "w") as f:
                f.write("---\n")
                for key, value in frontmatter.items():
                    if isinstance(value, list):
                        if value:
                            f.write(f"{key}: {value}\n")
                        else:
                            f.write(f"{key}: []\n")
                    else:
                        f.write(f"{key}: {value}\n")
                f.write("---\n\n")
                f.write(f"# {task_title}\n\n")

        return note_path

    def generate_obsidian_url(self, project_name: str, file_name: str) -> str:
        """Generate Obsidian URL for opening a specific file."""
        vault_name = self.get_obsidian_vault_name()

        # URL encode the file path
        file_path = f"10 Projects/{project_name}/{file_name}"
        encoded_path = urllib.parse.quote(file_path)

        return f"obsidian://open?vault={vault_name}&file={encoded_path}"

    def open_obsidian_note(self, project_name: str, file_name: str) -> bool:
        """Open an Obsidian note using the obsidian:// URL scheme."""
        url = self.generate_obsidian_url(project_name, file_name)

        try:
            # Use subprocess to open the URL with the default handler
            subprocess.run(["open", url], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
        except FileNotFoundError:
            # 'open' command not available (not on macOS)
            try:
                # Try with xdg-open (Linux)
                subprocess.run(["xdg-open", url], check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False


# Global config instance
config = Config()
