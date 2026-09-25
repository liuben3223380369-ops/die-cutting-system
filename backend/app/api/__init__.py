from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.master_data import router as master_data_router
from app.api.inventory import router as inventory_router
from app.api.purchase import router as purchase_router
from app.api.engineering import router as engineering_router
from app.api.planning import router as planning_router
from app.api.production import router as production_router
from app.api.production_board import router as production_board_router
from app.api.quality import router as quality_router
from app.api.costing import router as costing_router
from app.api.reporting import router as reporting_router
from app.api.period import router as period_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(master_data_router)
api_router.include_router(inventory_router)
api_router.include_router(purchase_router)
api_router.include_router(engineering_router)
api_router.include_router(planning_router)
api_router.include_router(production_router)
api_router.include_router(production_board_router)
api_router.include_router(quality_router)
api_router.include_router(costing_router)
api_router.include_router(reporting_router)
api_router.include_router(period_router)
