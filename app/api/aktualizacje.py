from fastapi import APIRouter

from app.schemas.aktualizacje import AktualizacjaOut
from app.services import aktualizacje_service

router = APIRouter(prefix="/aktualizacje", tags=["aktualizacje"])


@router.get("/sprawdz", response_model=AktualizacjaOut)
def sprawdz():
    return aktualizacje_service.sprawdz_dostepna_aktualizacje()
