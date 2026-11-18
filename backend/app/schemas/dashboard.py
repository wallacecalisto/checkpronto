from datetime import datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):

    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    # Percentual (0-100), não fração — o frontend só concatena "%".
    completion_rate: float
    checklist_divergent_count: int


class EmployeeRankingEntry(BaseModel):

    employee_id: int
    employee_name: str
    completed_count: int
    avg_execution_seconds: float | None
    on_time_count: int
    late_count: int
    # Percentual (0-100) entre as tarefas que tinham SLA configurado; nulo se
    # nenhuma das concluídas tinha `estimated_duration_minutes`.
    on_time_rate: float | None


class WeeklyTrendPoint(BaseModel):

    day_of_week: str
    completed_count: int
    avg_execution_seconds: float | None


class EmployeeProfileTaskEntry(BaseModel):
    id: int
    task_title: str
    started_at: datetime
    completed_at: datetime
    result: str
    estimated_duration_minutes: int | None
    duration_seconds: float
    # Nulo se a tarefa não tinha tempo estimado configurado no momento.
    on_time: bool | None
    # motivo digitado pelo funcionário (se algum) — mesmos campos
    # que já existiam em `task_assignments`, agora snapshotados no histórico.
    justification: str | None
    observation: str | None
    photo_url: str | None


class EmployeeProfile(BaseModel):

    employee_id: int
    employee_name: str
    completed_count: int
    avg_execution_seconds: float | None
    on_time_count: int
    late_count: int
    on_time_rate: float | None
    tasks: list[EmployeeProfileTaskEntry]


class ActivityFeedEntry(BaseModel):

    id: str
    actor_name: str
    description: str
    occurred_at: datetime


class ExceptionEntry(BaseModel):

    id: str
    type: str
    title: str
    user_name: str
    date: datetime
    reason: str | None


class RecentChecklistEntry(BaseModel):

    id: int
    template_name: str
    shift: str
    status: str
    fully_validated: bool
    executed_by_name: str
    validated_by_names: list[str]
    started_at: datetime
    finished_at: datetime | None
