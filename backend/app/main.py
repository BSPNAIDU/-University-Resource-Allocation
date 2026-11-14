from fastapi import FastAPI
from sqlalchemy import text

from backend.app.database import engine
from backend.app.core.config import settings

from backend.app.api.routes.auth import router as auth_router
from backend.app.api.routes.dashboard import router as dashboard_router
from backend.app.api.routes.students import router as students_router
from backend.app.api.routes.resources import router as resources_router
from backend.app.api.routes.examinations import router as examinations_router
from backend.app.api.routes.allocations import router as allocations_router
from backend.app.api.routes.registrations import router as registrations_router
from backend.app.api.routes.uploads import router as uploads_router
from backend.app.api.routes.comparison import router as comparison_router
from backend.app.api.routes.conflicts import router as conflicts_router
from backend.app.api.routes.exports import router as exports_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "Multi-University Smart Resource Allocation Platform "
        "using Greedy, Dynamic Programming, Exhaustive Search, "
        "Dynamic Reallocation, Conflict Detection, "
        "and Excel Seating Plan Exports."
    ),
    version="2.0.0",
)


app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router)
app.include_router(students_router)
app.include_router(resources_router)
app.include_router(examinations_router)
app.include_router(allocations_router)
app.include_router(registrations_router)
app.include_router(uploads_router)
app.include_router(comparison_router)
app.include_router(conflicts_router)
app.include_router(exports_router)


@app.get("/")
def home():
    return {
        "message": "Smart University Resource Allocation API is running",
        "project": settings.PROJECT_NAME,
        "version": "2.0.0",
    }


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception:
        return {"status": "unhealthy", "database": "disconnected"}

