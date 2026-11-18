from datetime import datetime

from pydantic import BaseModel


class TaskTimelineParticipant(BaseModel):

    employee_id: int
    employee_name: str
    worked_duration_seconds: int


class TaskTimelineSessionEntry(BaseModel):

    employee_id: int
    employee_name: str
    started_at: datetime
    ended_at: datetime | None
    leave_reason: str | None


class TaskTimelineBlockEntry(BaseModel):

    blocked_by_employee_id: int
    blocked_by_employee_name: str
    reason: str
    started_at: datetime
    ended_at: datetime | None


class TaskExecutionTimeline(BaseModel):

    execution_group_id: str
    task_id: int
    task_title: str
    created_by_user_name: str
    estimated_duration_minutes: int | None
    started_at: datetime
    completed_at: datetime
    total_elapsed_seconds: int
    result: str
    justification: str | None
    observation: str | None
    photo_url: str | None
    extra_photo_urls: list[str]
    participants: list[TaskTimelineParticipant]
    sessions: list[TaskTimelineSessionEntry]
    blocks: list[TaskTimelineBlockEntry]
