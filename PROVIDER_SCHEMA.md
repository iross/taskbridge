# Issue Provider Schema Design

## Core Data Models

### Universal Issue Model
```python
@dataclass
class UniversalIssue:
    id: str                          # Provider-specific ID
    title: str                       # Issue title
    description: Optional[str]       # Issue description
    state: IssueState               # Normalized state
    priority: IssuePriority         # Normalized priority
    assignee_id: Optional[str]      # Assignee identifier
    project_id: Optional[str]       # Project identifier
    labels: List[str]               # Issue labels/tags
    estimate: Optional[float]       # Time estimate
    url: str                        # Direct link to issue
    created_at: str                 # ISO timestamp
    updated_at: str                 # ISO timestamp
    custom_fields: Dict[str, Any]   # Provider-specific fields
```

### Universal Project Model
```python
@dataclass
class UniversalProject:
    id: str                          # Provider-specific ID
    name: str                       # Project name
    description: Optional[str]      # Project description
    state: ProjectState             # Normalized state
    progress: float                 # Progress percentage (0.0-1.0)
    labels: List[str]               # Project labels/tags
    url: str                        # Direct link to project
    custom_fields: Dict[str, Any]   # Provider-specific fields
```

## Abstract Provider Interface

### Core Provider Interface
```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

class IssueProvider(ABC):
    """Abstract interface for issue tracking systems."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'linear', 'todoist', 'taskwarrior')."""
        pass
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with the provider using given credentials."""
        pass
    
    @abstractmethod
    def get_projects(self) -> List[UniversalProject]:
        """Retrieve all projects from the provider."""
        pass
    
    @abstractmethod
    def get_issues(self, project_id: Optional[str] = None, 
                   query: Optional[str] = None, 
                   limit: int = 50) -> List[UniversalIssue]:
        """Retrieve issues, optionally filtered by project or search query."""
        pass
    
    @abstractmethod
    def create_comment(self, issue_id: str, body: str) -> bool:
        """Add a comment to an issue."""
        pass
    
    @abstractmethod
    def parse_client_project_name(self, 
                                  project_or_labels: Any) -> Tuple[Optional[str], Optional[str]]:
        """Extract client and project names from provider-specific data."""
        pass
```

### Provider Factory
```python
class ProviderFactory:
    """Factory for creating and managing issue providers."""
    
    _providers: Dict[str, type] = {}
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register a new provider implementation."""
        cls._providers[name] = provider_class
    
    @classmethod
    def create_provider(cls, provider_name: str, 
                       config: Dict[str, Any]) -> IssueProvider:
        """Create and configure a provider instance."""
        if provider_name not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        provider_class = cls._providers[provider_name]
        provider = provider_class()
        
        if not provider.authenticate(config):
            raise ValueError(f"Authentication failed for {provider_name}")
        
        return provider
```

## Configuration Schema

### Provider Configuration
```python
@dataclass
class ProviderConfig:
    name: str                       # Provider name
    enabled: bool                   # Whether provider is active
    credentials: Dict[str, Any]     # Authentication details
    settings: Dict[str, Any]        # Provider-specific settings
    
class MultiProviderConfig:
    active_provider: str            # Currently active provider
    providers: Dict[str, ProviderConfig]  # All configured providers
    
    def switch_provider(self, provider_name: str):
        """Switch to a different provider."""
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not configured")
        self.active_provider = provider_name
```

## Implementation Examples

### Linear Provider Implementation
```python
class LinearProvider(IssueProvider):
    @property
    def provider_name(self) -> str:
        return "linear"
    
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        self.api = LinearAPI(credentials.get("token"))
        return True
    
    def get_issues(self, project_id=None, query=None, limit=50):
        linear_issues = self.api.get_issues(project_id, query, limit)
        return [self._convert_issue(issue) for issue in linear_issues]
    
    def _convert_issue(self, linear_issue) -> UniversalIssue:
        return UniversalIssue(
            id=linear_issue.id,
            title=linear_issue.title,
            # ... map other fields
            custom_fields={"linear_state_id": linear_issue.state_id}
        )
```

### Todoist Provider Implementation
```python
class TodoistProvider(IssueProvider):
    @property
    def provider_name(self) -> str:
        return "todoist"
    
    def parse_client_project_name(self, project_or_labels):
        # Different parsing logic for Todoist labels
        return self._extract_from_todoist_labels(project_or_labels)
```

## Usage Pattern

```python
# Configuration
config = MultiProviderConfig(
    active_provider="linear",
    providers={
        "linear": ProviderConfig(
            name="linear",
            enabled=True,
            credentials={"token": "lin_..."},
            settings={}
        ),
        "todoist": ProviderConfig(
            name="todoist", 
            enabled=False,
            credentials={"token": "tod_..."},
            settings={"default_project": "Work"}
        )
    }
)

# Provider switching
provider = ProviderFactory.create_provider(
    config.active_provider, 
    config.providers[config.active_provider].credentials
)

# Use same interface regardless of provider
issues = provider.get_issues(limit=10)
provider.create_comment(issues[0].id, "Working on this")
```

This schema enables seamless provider swapping while maintaining consistent data models and operations across different issue tracking systems.