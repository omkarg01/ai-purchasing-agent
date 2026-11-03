from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.recommendations import router as recommendations_router
from app.api.catalog import router as catalog_router
from app.database.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="AI Purchasing Agent API",
    description="Intelligent purchasing decision, evaluation, and inventory risk API",
    version="0.1.0",
    lifespan=lifespan,
)

# Support both root-relative and /api-prefixed routes
app.include_router(recommendations_router)
app.include_router(recommendations_router, prefix="/api")
app.include_router(catalog_router)
app.include_router(catalog_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}

