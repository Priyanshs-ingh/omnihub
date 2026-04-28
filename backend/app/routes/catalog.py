from __future__ import annotations

from fastapi import APIRouter

from ..generator import catalog as catalog_mod
from ..models import CatalogResponse

router = APIRouter(tags=["catalog"])


@router.get("/catalog", response_model=CatalogResponse)
def get_catalog() -> CatalogResponse:
    return CatalogResponse(companies=catalog_mod.tiles())
