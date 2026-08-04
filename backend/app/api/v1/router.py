from fastapi import APIRouter

from app.api.v1.endpoints import auth, dashboard, green, health, knowledge, modules, projects, quality, reports, safety, users, work_orders, worker_care


api_router = APIRouter()
for endpoint in (health, modules, auth, users, projects, dashboard, safety, work_orders, worker_care, reports, knowledge, quality, green):
    api_router.include_router(endpoint.router)
