from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.core.config import settings
from backend.core.exceptions import (
    ContextBankException,
    TriggerNotFoundError,
    TriggerAlreadyExistsError,
    ContextNotFoundError,
    UnauthorizedAccessError,
    VersionNotFoundError,
    ValidationDomainError,
)
from backend.database.connection import engine, Base, SessionLocal
from backend.database.models import User
from backend.api.auth import router as auth_router, get_or_create_dev_user
from backend.api.triggers import router as triggers_router
from backend.api.contexts import router as contexts_router
from backend.api.search import router as search_router
from backend.api.versions import router as versions_router
from backend.api.integrations import router as integrations_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize schema
    Base.metadata.create_all(bind=engine)
    # Seed dev user
    db = SessionLocal()
    try:
        get_or_create_dev_user(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "A portable, trigger-based context management system for AI. "
        "Allows saving project decisions, architectures, and state under user-defined trigger words "
        "for instant retrieval by external AI applications."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(TriggerNotFoundError)
async def trigger_not_found_handler(request: Request, exc: TriggerNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": exc.code, "message": exc.message, "detail": exc.message, "trigger": exc.trigger},
    )


@app.exception_handler(TriggerAlreadyExistsError)
async def trigger_exists_handler(request: Request, exc: TriggerAlreadyExistsError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": exc.code, "message": exc.message, "trigger": exc.trigger},
    )


@app.exception_handler(ContextNotFoundError)
async def context_not_found_handler(request: Request, exc: ContextNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": exc.code, "message": exc.message, "context_id": exc.context_id},
    )


@app.exception_handler(UnauthorizedAccessError)
async def unauthorized_handler(request: Request, exc: UnauthorizedAccessError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"error": exc.code, "message": exc.message},
    )


@app.exception_handler(VersionNotFoundError)
async def version_not_found_handler(request: Request, exc: VersionNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": exc.code, "message": exc.message},
    )


@app.exception_handler(ValidationDomainError)
async def validation_error_handler(request: Request, exc: ValidationDomainError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": exc.code, "message": exc.message},
    )


# Register API Routers
app.include_router(auth_router)
app.include_router(triggers_router)
app.include_router(contexts_router)
app.include_router(search_router)
app.include_router(versions_router)
app.include_router(integrations_router)


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "health": "/api/v1/health",
        "status": "active",
    }
