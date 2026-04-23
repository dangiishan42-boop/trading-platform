import uvicorn

from app.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    uvicorn_kwargs = {
        "host": settings.host,
        "port": settings.port,
        "reload": settings.debug,
        "log_level": settings.log_level.lower(),
    }

    if not settings.debug and settings.web_concurrency > 1:
        uvicorn_kwargs["workers"] = settings.web_concurrency

    uvicorn.run("app.main:app", **uvicorn_kwargs)


if __name__ == "__main__":
    main()
