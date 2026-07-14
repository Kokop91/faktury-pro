from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.jpk import GotowoscOkresuJPK
from app.schemas.magazyn import RuchMagazynowyOut, StanMagazynowyOut
from app.services import jpk_service, raporty_service

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


@router.get("/jpk-v7/sprawdz", response_model=GotowoscOkresuJPK, tags=["jpk"])
def sprawdz_gotowosc_jpk(
    rok: int = Query(..., ge=1900, le=2100),
    miesiac: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    return jpk_service.sprawdz_gotowosc_okresu(db, rok, miesiac)


@router.get("/jpk-v7", tags=["jpk"])
def pobierz_jpk_v7(
    rok: int = Query(..., ge=1900, le=2100),
    miesiac: int = Query(..., ge=1, le=12),
    wariant: str = Query(..., pattern="^(miesieczny|kwartalny)$"),
    db: Session = Depends(get_db),
):
    xml_bytes = jpk_service.generuj_jpk_v7(db, rok, miesiac, wariant)
    przedrostek = "JPK_V7M" if wariant == "miesieczny" else "JPK_V7K"
    nazwa_pliku = f"{przedrostek}_{rok}-{miesiac:02d}.xml"
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{nazwa_pliku}"'},
    )
