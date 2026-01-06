from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.services.auth import get_current_user
from app.models.task import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskStatus,
    TaskPriority,
    TaskType,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# In-memory task storage (will be replaced with Supabase)
tasks_db: Dict[str, Dict[str, Any]] = {}


@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    store_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    task_type: Optional[TaskType] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user)
):
    """Get all tasks."""
    tasks = list(tasks_db.values())

    if store_id:
        tasks = [t for t in tasks if t.get("store_id") == store_id]
    if status:
        tasks = [t for t in tasks if t.get("status") == status]
    if priority:
        tasks = [t for t in tasks if t.get("priority") == priority]
    if task_type:
        tasks = [t for t in tasks if t.get("task_type") == task_type]

    # Sort by priority (urgent first) then by created_at
    priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    tasks.sort(key=lambda x: (priority_order.get(x.get("priority", "medium"), 2), x.get("created_at", "")))

    total = len(tasks)
    tasks = tasks[offset:offset + limit]

    return tasks


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific task."""
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    return tasks_db[task_id]


@router.post("", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create a new task."""
    task_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    task_data = {
        "id": task_id,
        "store_id": task.store_id,
        "product_id": task.product_id,
        "title": task.title,
        "description": task.description,
        "task_type": task.task_type,
        "priority": task.priority,
        "status": TaskStatus.PENDING,
        "metadata": task.metadata,
        "result": None,
        "started_at": None,
        "completed_at": None,
        "created_at": now,
        "updated_at": now,
    }

    tasks_db[task_id] = task_data
    return task_data


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    updates: TaskUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update a task."""
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task = tasks_db[task_id]
    update_data = updates.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        task[field] = value

    # Handle status transitions
    if "status" in update_data:
        if update_data["status"] == TaskStatus.IN_PROGRESS and not task.get("started_at"):
            task["started_at"] = datetime.utcnow().isoformat()
        elif update_data["status"] == TaskStatus.COMPLETED:
            task["completed_at"] = datetime.utcnow().isoformat()

    task["updated_at"] = datetime.utcnow().isoformat()
    tasks_db[task_id] = task

    return task


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a task."""
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    del tasks_db[task_id]
    return {"message": "Task deleted successfully"}


@router.post("/{task_id}/start")
async def start_task(
    task_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Start a task."""
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task = tasks_db[task_id]
    task["status"] = TaskStatus.IN_PROGRESS
    task["started_at"] = datetime.utcnow().isoformat()
    task["updated_at"] = datetime.utcnow().isoformat()

    return task


@router.post("/{task_id}/complete")
async def complete_task(
    task_id: str,
    result: Optional[Dict[str, Any]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Complete a task."""
    if task_id not in tasks_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )

    task = tasks_db[task_id]
    task["status"] = TaskStatus.COMPLETED
    task["completed_at"] = datetime.utcnow().isoformat()
    task["updated_at"] = datetime.utcnow().isoformat()
    if result:
        task["result"] = result

    return task


@router.get("/stats/summary")
async def get_task_stats(
    store_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get task statistics."""
    tasks = list(tasks_db.values())

    if store_id:
        tasks = [t for t in tasks if t.get("store_id") == store_id]

    stats = {
        "total": len(tasks),
        "pending": len([t for t in tasks if t.get("status") == TaskStatus.PENDING]),
        "in_progress": len([t for t in tasks if t.get("status") == TaskStatus.IN_PROGRESS]),
        "completed": len([t for t in tasks if t.get("status") == TaskStatus.COMPLETED]),
        "failed": len([t for t in tasks if t.get("status") == TaskStatus.FAILED]),
        "by_priority": {
            "urgent": len([t for t in tasks if t.get("priority") == TaskPriority.URGENT]),
            "high": len([t for t in tasks if t.get("priority") == TaskPriority.HIGH]),
            "medium": len([t for t in tasks if t.get("priority") == TaskPriority.MEDIUM]),
            "low": len([t for t in tasks if t.get("priority") == TaskPriority.LOW]),
        },
        "by_type": {}
    }

    for task_type in TaskType:
        stats["by_type"][task_type.value] = len([t for t in tasks if t.get("task_type") == task_type])

    return stats
