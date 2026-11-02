from fastapi import FastAPI
from app.api.recommendations import router as recommendations_router

app = FastAPI(
    title="AI Purchasing Agent API",
    description="Intelligent purchasing decision, evaluation, and inventory risk API",
    version="0.1.0",
)

# Support both root-relative and /api-prefixed routes
app.include_router(recommendations_router)
app.include_router(recommendations_router, prefix="/api")


@app.get("/health")
def health_check():
    return {"status": "ok"}
