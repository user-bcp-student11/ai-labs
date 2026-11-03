# get-api-tasks.component

```mermaid
flowchart LR
    A[Client] --> B[FastAPI Router\nGET /api/tasks]
    B --> C[Security Dependency\nlegacy_identity]
    B --> D[RequirementService.list_tasks]
    D --> E[_authorized_owner]
    D --> F[TaskRepository.list_by_owner]
    F --> G[(SQLite tasks)]
    D --> H[_as_task mapper]
    H --> I[TaskResponse[]]

```
