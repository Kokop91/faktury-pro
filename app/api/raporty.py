from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.magazyn import RuchMagazynowyOut, StanMagazynowyOut
from app.services import raporty_service

router = APIRouter(prefix="/raporty", tags=["magazyn"])


@router.get("/historia-ruchow", response_model=list[RuchMagazynowyOut])
def historia_ruchow(
    magazyn_id: int | None = Query(default=None),
    data_od: date | None = Query(default=None),
    data_do: date | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return raporty_service.historia_ruchow_magazynu(db, magazyn_id, data_od, data_do)


@router.get("/ponizej-minimum", response_model=list[StanMagazynowyOut])
def ponizej_minimum(
    magazyn_id: int | None = Query(default=None), db: Session = Depends(get_db)
):
    return raporty_service.lista_ponizej_minimum(db, magazyn_id)
