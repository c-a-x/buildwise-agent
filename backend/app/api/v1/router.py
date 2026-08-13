from fastapi import APIRouter

from app.api.v1.endpoints import audit, auth, dashboard, green, hardware, health, knowledge, modules, projects, quality, reports, safety, stats, users, wellbeing, work_orders, worker_care


api_router = APIRouter()
for endpoint in (health, modules, auth, users, projects, dashboard, safety, work_orders, worker_care, wellbeing, reports, knowledge, quality, green, stats, audit, hardware):
    api_router.include_router(endpoint.router)
