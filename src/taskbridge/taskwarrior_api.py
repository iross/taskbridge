"""Taskwarrior API client implementation."""

import json
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer


@dataclass
class TaskWarriorTask:
    """Taskwarrior task data model."""
    
    uuid: str
    description: str
    status: str = "pending"
    project: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    due: Optional[str] = None
    entry: Optional[str] = None
    modified: Optional[str] = None
    urgency: Optional[float] = None
    annotations: Optional[List[Dict[str, str]]] = None
    estimate: Optional[str] = None
    
    # Store all other fields as custom_fields
    custom_fields: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.tags is None:
            self.tags = []
        if self.annotations is None:
            self.annotations = []
        if self.custom_fields is None:
            self.custom_fields = {}


@dataclass 
class TaskWarriorProject:
    """Taskwarrior project representation."""
    
    name: str
    description: Optional[str] = None
    tasks_count: int = 0
    pending_count: int = 0
    completed_count: int = 0


class TaskWarriorAPI:
    """API client for Taskwarrior using CLI commands."""
    
    def __init__(self, task_cmd: str = "task"):
        """Initialize TaskWarrior API client.
        
        Args:
            task_cmd: Path to the task command (default: "task")
        """
        self.task_cmd = task_cmd
        self._verify_taskwarrior()
    
    def _verify_taskwarrior(self) -> None:
        """Verify that Taskwarrior is available."""
        try:
            result = subprocess.run(
                [self.task_cmd, "version"], 
                capture_output=True, 
                text=True,
                check=True
            )
            if "task" not in result.stdout.lower():
                raise ValueError("Invalid Taskwarrior installation")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise ValueError(f"Taskwarrior not available: {e}")
    
    def _run_task_command(self, args: List[str], input_data: str = None) -> str:
        """Run a task command and return output.
        
        Args:
            args: Command arguments
            input_data: Optional input data for stdin
            
        Returns:
            Command output as string
            
        Raises:
            RuntimeError: If command fails
        """
        try:
            cmd = [self.task_cmd] + args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                input=input_data,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Task command failed: {e.stderr}")
    
    def get_all_tasks(self, status: Optional[str] = None) -> List[TaskWarriorTask]:
        """Get all tasks, optionally filtered by status.
        
        Args:
            status: Optional status filter (pending, completed, etc.)
            
        Returns:
            List of TaskWarrior tasks
        """
        args = ["export"]
        # Don't add status filter to export, filter in Python instead
        
        output = self._run_task_command(args)
        
        if not output.strip():
            return []
        
        try:
            task_data = json.loads(output)
            tasks = [self._dict_to_task(task_dict) for task_dict in task_data]
            
            # Filter by status if specified
            if status:
                tasks = [task for task in tasks if task.status == status]
            
            return tasks
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse task export: {e}")
    
    def get_pending_tasks(self) -> List[TaskWarriorTask]:
        """Get all pending tasks."""
        return self.get_all_tasks(status="pending")
    
    def get_completed_tasks(self) -> List[TaskWarriorTask]:
        """Get all completed tasks.""" 
        return self.get_all_tasks(status="completed")
    
    def get_tasks_by_project(self, project_name: str) -> List[TaskWarriorTask]:
        """Get tasks filtered by project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            List of tasks in the project
        """
        # Get all tasks and filter in Python
        all_tasks = self.get_all_tasks()
        return [task for task in all_tasks if task.project == project_name]
    
    def get_task_by_uuid(self, task_uuid: str) -> Optional[TaskWarriorTask]:
        """Get a specific task by UUID.
        
        Args:
            task_uuid: Task UUID
            
        Returns:
            TaskWarrior task or None if not found
        """
        try:
            output = self._run_task_command(["export", task_uuid])
            if not output.strip():
                return None
                
            task_data = json.loads(output)
            if not task_data:
                return None
                
            return self._dict_to_task(task_data[0])
        except (json.JSONDecodeError, RuntimeError):
            return None
    
    def create_task(self, task: TaskWarriorTask) -> TaskWarriorTask:
        """Create a new task.
        
        Args:
            task: Task to create
            
        Returns:
            Created task with updated fields
        """
        # Convert task to dict for JSON import
        task_dict = self._task_to_dict(task)
        
        # Generate a valid UUID for new tasks
        task_dict["uuid"] = str(uuid.uuid4())
        
        # Create temporary file for import
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([task_dict], f)
            temp_file = f.name
        
        try:
            self._run_task_command(["import", temp_file])
            
            # Get the created task by UUID
            created_task = self.get_task_by_uuid(task_dict["uuid"])
            if created_task:
                return created_task
            else:
                # Fallback: find by description and project
                all_tasks = self.get_all_tasks()
                for t in reversed(all_tasks):  # Most recent first
                    if t.description == task.description and t.project == task.project:
                        return t
                return task
            
        finally:
            # Clean up temp file
            Path(temp_file).unlink(missing_ok=True)
    
    def update_task(self, task_uuid: str, updates: Dict[str, Any]) -> bool:
        """Update an existing task.
        
        Args:
            task_uuid: UUID of task to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build modify command
            modify_args = [task_uuid, "modify"]
            
            for key, value in updates.items():
                if key == "tags":
                    # Handle tags specially - replace all tags
                    if value:
                        modify_args.append(f"tags:{','.join(value)}")
                    else:
                        modify_args.append("tags:")
                elif key == "project":
                    modify_args.append(f"project:{value}" if value else "project:")
                elif key == "priority":
                    modify_args.append(f"priority:{value}" if value else "priority:")
                elif key == "due":
                    modify_args.append(f"due:{value}" if value else "due:")
                elif key == "description":
                    modify_args.append(f"description:{value}")
            
            self._run_task_command(modify_args)
            return True
            
        except RuntimeError:
            return False
    
    def delete_task(self, task_uuid: str) -> bool:
        """Delete a task.
        
        Args:
            task_uuid: UUID of task to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._run_task_command([task_uuid, "delete"], input_data="yes\n")
            return True
        except RuntimeError:
            return False
    
    def complete_task(self, task_uuid: str) -> bool:
        """Mark a task as completed.
        
        Args:
            task_uuid: UUID of task to complete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._run_task_command([task_uuid, "done"])
            return True
        except RuntimeError:
            return False
    
    def get_projects(self) -> List[TaskWarriorProject]:
        """Get all projects with task counts.
        
        Returns:
            List of projects
        """
        # Get project statistics
        try:
            output = self._run_task_command(["projects"])
            projects = []
            
            # Parse the projects output
            lines = output.strip().split('\n')
            for line in lines:
                if line.strip() and not line.startswith('Project') and '---' not in line:
                    # Parse project line (format varies but generally: Project Tasks Remaining)
                    parts = line.split()
                    if len(parts) >= 2:
                        project_name = parts[0]
                        try:
                            tasks_count = int(parts[1]) if len(parts) > 1 else 0
                            remaining_count = int(parts[2]) if len(parts) > 2 else 0
                            completed_count = tasks_count - remaining_count
                            
                            projects.append(TaskWarriorProject(
                                name=project_name,
                                tasks_count=tasks_count,
                                pending_count=remaining_count,
                                completed_count=completed_count
                            ))
                        except ValueError:
                            # Skip malformed lines
                            continue
            
            return projects
            
        except RuntimeError:
            return []
    
    def add_annotation(self, task_uuid: str, annotation: str) -> bool:
        """Add an annotation to a task.
        
        Args:
            task_uuid: Task UUID
            annotation: Annotation text
            
        Returns:
            True if successful
        """
        try:
            self._run_task_command([task_uuid, "annotate", annotation])
            return True
        except RuntimeError:
            return False
    
    def _dict_to_task(self, task_dict: Dict[str, Any]) -> TaskWarriorTask:
        """Convert dictionary from Taskwarrior export to TaskWarriorTask.
        
        Args:
            task_dict: Task dictionary from JSON export
            
        Returns:
            TaskWarriorTask object
        """
        # Extract known fields
        known_fields = {
            'uuid', 'description', 'status', 'project', 'priority', 
            'tags', 'due', 'entry', 'modified', 'urgency', 
            'annotations', 'estimate', 'id'
        }
        
        # Custom fields are everything else
        custom_fields = {k: v for k, v in task_dict.items() if k not in known_fields}
        
        return TaskWarriorTask(
            uuid=task_dict.get('uuid', ''),
            description=task_dict.get('description', ''),
            status=task_dict.get('status', 'pending'),
            project=task_dict.get('project'),
            priority=task_dict.get('priority'),
            tags=task_dict.get('tags', []),
            due=task_dict.get('due'),
            entry=task_dict.get('entry'),
            modified=task_dict.get('modified'),
            urgency=task_dict.get('urgency'),
            annotations=task_dict.get('annotations', []),
            estimate=task_dict.get('estimate'),
            custom_fields=custom_fields
        )
    
    def _task_to_dict(self, task: TaskWarriorTask) -> Dict[str, Any]:
        """Convert TaskWarriorTask to dictionary for JSON export.
        
        Args:
            task: TaskWarriorTask object
            
        Returns:
            Dictionary suitable for JSON import
        """
        result = {
            'uuid': task.uuid,
            'description': task.description,
            'status': task.status,
        }
        
        # Add optional fields if they exist
        if task.project:
            result['project'] = task.project
        if task.priority:
            result['priority'] = task.priority
        if task.tags:
            result['tags'] = task.tags
        if task.due:
            result['due'] = task.due
        if task.entry:
            result['entry'] = task.entry
        if task.modified:
            result['modified'] = task.modified
        if task.urgency is not None:
            result['urgency'] = task.urgency
        if task.annotations:
            result['annotations'] = task.annotations
        if task.estimate:
            result['estimate'] = task.estimate
        
        # Add custom fields
        if task.custom_fields:
            result.update(task.custom_fields)
        
        return result


# Global TaskWarrior API instance
try:
    taskwarrior_api = TaskWarriorAPI()
except ValueError:
    # TaskWarrior not available
    taskwarrior_api = None