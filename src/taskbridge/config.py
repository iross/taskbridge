"""Configuration management for TaskBridge."""

import os
import yaml
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import typer


class Config:
    """Configuration management for TaskBridge."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".taskbridge"
        self.config_file = self.config_dir / "config.yaml"
        self._config_data: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
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
    
    def validate_linear_token(self, token: str) -> bool:
        """Validate Linear API token."""
        try:
            headers = {'Authorization': token, 'Content-Type': 'application/json'}
            # Test with a simple GraphQL query
            payload = {"query": "query { viewer { id name } }"}
            response = requests.post('https://api.linear.app/graphql', headers=headers, json=payload, timeout=10)
            
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
            response = requests.get('https://api.track.toggl.com/api/v9/me', auth=auth, timeout=10)
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
            typer.echo("❌ Invalid Linear token. Please check your token and try again.")
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