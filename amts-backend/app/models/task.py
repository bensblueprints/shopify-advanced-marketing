from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskType(str, Enum):
    CONTENT_GENERATION = "content_generation"
    PRODUCT_SYNC = "product_sync"
    THEME_UPDATE = "theme_update"
    IMAGE_OPTIMIZATION = "image_optimization"
    SEO_OPTIMIZATION = "seo_optimization"
    BULK_IMPORT = "bulk_import"
    CUSTOM = "custom"


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: TaskType
    priority: TaskPriority = TaskPriority.MEDIUM
    metadata: Optional[Dict[str, Any]] = None


class TaskCreate(TaskBase):
    store_id: str
    product_id: Optional[str] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


class Task(TaskBase):
    id: str
    store_id: str
    product_id: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskResponse(BaseModel):
    id: str
    store_id: str
    product_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    task_type: TaskType
    priority: TaskPriority
    status: TaskStatus
    metadata: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
