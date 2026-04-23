from fastapi import APIRouter
router = APIRouter(prefix="/strategy-builder", tags=["strategy-builder"])

@router.get("/schema")
def strategy_builder_schema():
    return {
        "fields": [
            {"name": "strategy_name", "type": "string"},
            {"name": "parameters", "type": "object"},
            {"name": "entry_rule", "type": "string"},
            {"name": "exit_rule", "type": "string"},
        ]
    }
