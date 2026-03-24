from fastapi import FastAPI
from app.routers import health, research, schemas, categories
from app.blog.api.router import router as blog_router

app = FastAPI(
    title="IRA API - Iterative Research Agent",
    description="API-based iterative research agent for food news",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(research.router)
app.include_router(schemas.router)
app.include_router(categories.router)
app.include_router(blog_router)
