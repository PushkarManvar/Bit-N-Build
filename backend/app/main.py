from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import AppError
from app.schemas.errors import ErrorResponse


def create_app() -> FastAPI:
    application = FastAPI(
        title="JourneyLens API",
        version="0.1.0",
        description=(
            "Explainable identity resolution and broken-journey detection "
            "for synthetic e-commerce refund events."
        ),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    application.add_exception_handler(AppError, _handle_app_error)
    application.add_exception_handler(RequestValidationError, _handle_validation_error)
    return application


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    body = ErrorResponse(
        error={
            "code": exc.code,
            "message": exc.message,
            "stage": exc.stage,
            "raw_event_id": exc.raw_event_id,
            "details": exc.details,
        }
    )
    return JSONResponse(status_code=exc.http_status, content=body.model_dump(mode="json"))


async def _handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    body = ErrorResponse(
        error={
            "code": "VALIDATION_ERROR",
            "message": "Event envelope failed validation.",
            "stage": "validation",
            "raw_event_id": None,
            "details": {"errors": exc.errors()},
        }
    )
    return JSONResponse(status_code=422, content=body.model_dump(mode="json"))


app = create_app()