from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    DataValidationError,
    InvalidRequestError,
    ResourceConflictError,
    StrategyNotFoundError,
)


def _error_response(status_code: int, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"detail": detail})


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StrategyNotFoundError)
    async def handle_strategy_not_found(_: Request, exc: StrategyNotFoundError) -> JSONResponse:
        return _error_response(status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(FileNotFoundError)
    async def handle_file_not_found(_: Request, exc: FileNotFoundError) -> JSONResponse:
        return _error_response(status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(DataValidationError)
    async def handle_data_validation(_: Request, exc: DataValidationError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.exception_handler(InvalidRequestError)
    async def handle_invalid_request(_: Request, exc: InvalidRequestError) -> JSONResponse:
        return _error_response(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.exception_handler(ResourceConflictError)
    async def handle_resource_conflict(_: Request, exc: ResourceConflictError) -> JSONResponse:
        return _error_response(status.HTTP_409_CONFLICT, str(exc))
