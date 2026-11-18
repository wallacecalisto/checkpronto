from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.checklist_templates import items_router as checklist_template_items_router
from app.api.v1.checklist_templates import router as checklist_templates_router
from app.api.v1.checklists import router as checklists_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.employees import router as employees_router
from app.api.v1.sectors import router as sectors_router
from app.api.v1.store_settings import router as store_settings_router
from app.api.v1.stores import router as stores_router
from app.api.v1.task_assignments import router as task_assignments_router
from app.api.v1.task_execution_history import router as task_execution_history_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(stores_router)
api_router.include_router(store_settings_router)
api_router.include_router(employees_router)
api_router.include_router(sectors_router)
api_router.include_router(users_router)
api_router.include_router(tasks_router)
api_router.include_router(task_assignments_router)
api_router.include_router(task_execution_history_router)
api_router.include_router(checklist_templates_router)
api_router.include_router(checklist_template_items_router)
api_router.include_router(checklists_router)
api_router.include_router(audit_router)
api_router.include_router(dashboard_router)
