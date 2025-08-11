"""Synchronization engine for TaskBridge."""

import typer
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from .linear_api import linear_api, LinearProject
from .toggl_api import toggl_api, TogglClient, TogglProject
from .database import db, Project as DbProject


@dataclass
class SyncAction:
    """Represents a synchronization action to be taken."""
    action_type: str  # 'create_client', 'create_project', 'update_mapping', 'skip'
    description: str
    linear_project: Optional[LinearProject] = None
    toggl_client: Optional[TogglClient] = None
    toggl_project: Optional[TogglProject] = None
    client_name: Optional[str] = None
    project_name: Optional[str] = None


class SyncEngine:
    """Handles synchronization between Linear and Toggl."""
    
    def __init__(self):
        if not linear_api:
            raise ValueError("Linear API not configured")
        if not toggl_api:
            raise ValueError("Toggl API not configured")
        
        self.linear = linear_api
        self.toggl = toggl_api
    
    def analyze_sync_state(self) -> Tuple[List[SyncAction], List[LinearProject]]:
        """Analyze current state and determine what sync actions are needed.
        
        Returns:
            Tuple of (sync_actions, projects_without_format)
        """
        # Get current data from both systems
        linear_projects = self.linear.get_projects_with_parsed_names()
        toggl_clients = {client.name: client for client in self.toggl.get_clients()}
        toggl_projects = self.toggl.get_projects()
        existing_mappings = {mapping.linear_id: mapping for mapping in db.get_all_projects()}
        
        sync_actions = []
        projects_without_format = []
        
        for linear_project, client_name, project_name in linear_projects:
            # Skip if project doesn't follow #client/CLIENT_NAME format
            if not client_name or not project_name:
                projects_without_format.append(linear_project)
                continue
            
            # Check if we already have a mapping for this Linear project
            if linear_project.id in existing_mappings:
                # TODO: Could add logic to verify the mapping is still valid
                continue
            
            # Find or create Toggl client
            toggl_client = toggl_clients.get(client_name)
            if not toggl_client:
                sync_actions.append(SyncAction(
                    action_type='create_client',
                    description=f'Create Toggl client: {client_name}',
                    linear_project=linear_project,
                    client_name=client_name,
                    project_name=project_name
                ))
            else:
                # Find Toggl project under this client
                matching_toggl_project = None
                for tp in toggl_projects:
                    if tp.cid == toggl_client.id and tp.name == project_name:
                        matching_toggl_project = tp
                        break
                
                if not matching_toggl_project:
                    sync_actions.append(SyncAction(
                        action_type='create_project',
                        description=f'Create Toggl project: {project_name} under client {client_name}',
                        linear_project=linear_project,
                        toggl_client=toggl_client,
                        client_name=client_name,
                        project_name=project_name
                    ))
                else:
                    sync_actions.append(SyncAction(
                        action_type='update_mapping',
                        description=f'Create mapping: {linear_project.name} -> {client_name}/{project_name}',
                        linear_project=linear_project,
                        toggl_client=toggl_client,
                        toggl_project=matching_toggl_project,
                        client_name=client_name,
                        project_name=project_name
                    ))
        
        return sync_actions, projects_without_format
    
    def preview_sync(self) -> None:
        """Show a preview of sync actions without executing them."""
        try:
            sync_actions, projects_without_format = self.analyze_sync_state()
            
            if not sync_actions and not projects_without_format:
                typer.echo("✅ Everything is already in sync!")
                return
            
            if sync_actions:
                typer.echo("Sync Actions to be Performed:")
                typer.echo("=" * 40)
                
                for i, action in enumerate(sync_actions, 1):
                    typer.echo(f"{i}. {action.description}")
                
                typer.echo()
            
            if projects_without_format:
                typer.echo("Projects Not Following #client/CLIENT_NAME Format:")
                typer.echo("=" * 50)
                
                for project in projects_without_format:
                    typer.echo(f"- {project.name}")
                
                typer.echo("\nThese projects will be skipped during sync.")
                typer.echo("To sync them, add #client/CLIENT_NAME labels.")
                typer.echo()
            
        except Exception as e:
            typer.echo(f"❌ Error analyzing sync state: {e}")
            raise typer.Exit(1)
    
    def execute_sync(self, dry_run: bool = False) -> None:
        """Execute synchronization actions."""
        try:
            sync_actions, projects_without_format = self.analyze_sync_state()
            
            if not sync_actions:
                typer.echo("✅ Nothing to sync!")
                return
            
            # Show preview
            self.preview_sync()
            
            if not dry_run:
                # Ask for confirmation
                if not typer.confirm("Proceed with sync?"):
                    typer.echo("Sync cancelled.")
                    return
            
            # Execute actions
            typer.echo("Executing sync actions...")
            typer.echo("-" * 30)
            
            for action in sync_actions:
                if dry_run:
                    typer.echo(f"[DRY RUN] {action.description}")
                    continue
                
                try:
                    self._execute_action(action)
                    typer.echo(f"✅ {action.description}")
                    
                    # Log the action
                    db.log_sync_action(action.action_type, {
                        'description': action.description,
                        'linear_project_id': action.linear_project.id if action.linear_project else None,
                        'toggl_client_id': action.toggl_client.id if action.toggl_client else None,
                        'toggl_project_id': action.toggl_project.id if action.toggl_project else None
                    })
                    
                except Exception as e:
                    typer.echo(f"❌ Failed: {action.description} - {e}")
                    # Continue with other actions
            
            typer.echo("\n✅ Sync completed!")
            
        except Exception as e:
            typer.echo(f"❌ Error during sync: {e}")
            raise typer.Exit(1)
    
    def _execute_action(self, action: SyncAction) -> None:
        """Execute a single sync action."""
        if action.action_type == 'create_client':
            # Create Toggl client
            toggl_client = self.toggl.create_client(action.client_name)
            
            # Create Toggl project under the new client
            toggl_project = self.toggl.create_project(action.project_name, toggl_client.id)
            
            # Create database mapping
            db_project = DbProject(
                linear_id=action.linear_project.id,
                linear_name=action.linear_project.name,
                toggl_client_id=str(toggl_client.id),
                toggl_project_id=str(toggl_project.id)
            )
            db.create_project(db_project)
            
        elif action.action_type == 'create_project':
            # Create Toggl project under existing client
            toggl_project = self.toggl.create_project(action.project_name, action.toggl_client.id)
            
            # Create database mapping
            db_project = DbProject(
                linear_id=action.linear_project.id,
                linear_name=action.linear_project.name,
                toggl_client_id=str(action.toggl_client.id),
                toggl_project_id=str(toggl_project.id)
            )
            db.create_project(db_project)
            
        elif action.action_type == 'update_mapping':
            # Create database mapping for existing Toggl client/project
            db_project = DbProject(
                linear_id=action.linear_project.id,
                linear_name=action.linear_project.name,
                toggl_client_id=str(action.toggl_client.id),
                toggl_project_id=str(action.toggl_project.id)
            )
            db.create_project(db_project)


# Global sync engine instance (will be None if APIs not configured)
try:
    sync_engine = SyncEngine()
except ValueError:
    sync_engine = None