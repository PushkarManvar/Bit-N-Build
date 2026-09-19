from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "journeylens-backend"}


@router.get("/ready")
def ready() -> dict[str, str]:
    # The database readiness check will be added with the persistence slice.
    return {"status": "ready"}
