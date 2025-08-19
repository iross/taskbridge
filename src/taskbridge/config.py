"""Configuration management for TaskBridge."""

import subprocess
import urllib.parse
from pathlib import Path
from typing import Any, Optional

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
            with open(self.config_file, 'w') as f:
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

    def get_linear_token(self) -> Optional[str]:
        """Get Linear API token."""
        return self.get('linear_token')

    def get_toggl_token(self) -> Optional[str]:
        """Get Toggl API token."""
        return self.get('toggl_token')

    def get_obsidian_vault_path(self) -> Optional[str]:
        """Get Obsidian vault path."""
        return self.get('obsidian_vault_path')

    def get_obsidian_vault_name(self) -> Optional[str]:
        """Get Obsidian vault name."""
        return self.get('obsidian_vault_name', 'obsidian')
    
    def get_taskwarrior_cmd(self) -> str:
        """Get Taskwarrior command path."""
        return self.get('taskwarrior_cmd', 'task')
    
    def set_taskwarrior_cmd(self, cmd_path: str) -> None:
        """Set Taskwarrior command path."""
        self.set('taskwarrior_cmd', cmd_path)
    
    def get_taskwarrior_enabled(self) -> bool:
        """Check if Taskwarrior integration is enabled."""
        return self.get('taskwarrior_enabled', False)
    
    def set_taskwarrior_enabled(self, enabled: bool) -> None:
        """Enable or disable Taskwarrior integration."""
        self.set('taskwarrior_enabled', enabled)

    def set_obsidian_config(
        self, vault_path: str, vault_name: str = 'obsidian'
    ) -> None:
        """Set Obsidian vault configuration."""
        # Validate the vault path exists
        vault_path_obj = Path(vault_path).expanduser()
        if not vault_path_obj.exists():
            raise ValueError(f"Vault path does not exist: {vault_path}")
        if not vault_path_obj.is_dir():
            raise ValueError(f"Vault path is not a directory: {vault_path}")

        self.set('obsidian_vault_path', str(vault_path_obj))
        self.set('obsidian_vault_name', vault_name)

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
        tags: list = None,
    ) -> Path:
        """Create a task-specific note with frontmatter."""
        if tags is None:
            tags = []

        project_dir = self.create_project_directory(project_name)

        # Sanitize filename
        safe_title = "".join(
            c for c in task_title if c.isalnum() or c in (' ', '-', '_')
        ).rstrip()
        note_path = project_dir / f"{safe_title}.md"

        # Create frontmatter
        frontmatter = {
            'fileClass': 'task',
            'project': project_name,
            'status': status,
            'client': client,
            'tags': tags,
            'due': ''
        }

        # Only create the note if it doesn't already exist
        if not note_path.exists():
            # Write the note with frontmatter
            with open(note_path, 'w') as f:
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
            subprocess.run(['open', url], check=True)
            return True
        except subprocess.CalledProcessError:
            return False
        except FileNotFoundError:
            # 'open' command not available (not on macOS)
            try:
                # Try with xdg-open (Linux)
                subprocess.run(['xdg-open', url], check=True)
                return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False

    def validate_linear_token(self, token: str) -> bool:
        """Validate Linear API token."""
        try:
            headers = {'Authorization': token, 'Content-Type': 'application/json'}
            # Test with a simple GraphQL query
            payload = {"query": "query { viewer { id name } }"}
            response = requests.post(
                'https://api.linear.app/graphql',
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                return False

            data = response.json()
            return 'errors' not in data and 'viewer' in data.get('data', {})
        except Exception:
            return False

    def validate_toggl_token(self, token: str) -> bool:
        """Validate Toggl API token."""
        try:
            auth = (token, 'api_token')
            response = requests.get(
                'https://api.track.toggl.com/api/v9/me', auth=auth, timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

    def setup_interactive(self) -> None:
        """Interactive configuration setup."""
        typer.echo("TaskBridge Configuration Setup")
        typer.echo("=" * 35)

        # Get Linear token
        current_linear = self.get_linear_token()
        if current_linear:
            typer.echo(f"Current Linear token: {current_linear[:8]}...")
            if not typer.confirm("Update Linear token?"):
                linear_token = current_linear
            else:
                linear_token = typer.prompt("Enter Linear API token")
        else:
            linear_token = typer.prompt("Enter Linear API token")

        # Validate Linear token
        typer.echo("Validating Linear token...")
        if not self.validate_linear_token(linear_token):
            typer.echo(
                "❌ Invalid Linear token. Please check your token and try again."
            )
            raise typer.Exit(1)
        typer.echo("✅ Linear token is valid")

        # Get Toggl token
        current_toggl = self.get_toggl_token()
        if current_toggl:
            typer.echo(f"Current Toggl token: {current_toggl[:8]}...")
            if not typer.confirm("Update Toggl token?"):
                toggl_token = current_toggl
            else:
                toggl_token = typer.prompt("Enter Toggl API token")
        else:
            toggl_token = typer.prompt("Enter Toggl API token")

        # Validate Toggl token
        typer.echo("Validating Toggl token...")
        if not self.validate_toggl_token(toggl_token):
            typer.echo("❌ Invalid Toggl token. Please check your token and try again.")
            raise typer.Exit(1)
        typer.echo("✅ Toggl token is valid")

        # Save configuration
        self.set('linear_token', linear_token)
        self.set('toggl_token', toggl_token)

        typer.echo(f"✅ Configuration saved to {self.config_file}")
        typer.echo("You can now use TaskBridge commands!")


# Global config instance
config = Config()

