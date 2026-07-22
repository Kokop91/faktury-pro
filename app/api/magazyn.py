from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import TypDokumentuMagazynowego
from app.schemas.magazyn import (
    DokumentMagazynowyCreate,
    DokumentMagazynowyOut,
    DokumentMagazynowyUpdate,
    StanMagazynowyOut,
    UtworzenieDokumentuMagazynowegoOut,
)
from app.services import magazyn_service

router = APIRouter(tags=["magazyn"])


@router.post(
    "/dokumenty-magazynowe",
    response_model=UtworzenieDokumentuMagazynowegoOut,
    status_code=201,
)
def utworz_dokument_magazynowy(
    dane: DokumentMagazynowyCreate, db: Session = Depends(get_db)
):
    dokument, ostrzezenia = magazyn_service.utworz_dokument_magazynowy(db, dane)
    return UtworzenieDokumentuMagazynowegoOut(
        dokument=dokument, ostrzezenia=ostrzezenia
    )


@router.get("/dokumenty-magazynowe", response_model=list[DokumentMagazynowyOut])
def lista_dokumentow_magazynowych(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    typ: TypDokumentuMagazynowego | None = Query(default=None),
    magazyn_id: int | None = Query(default=None),
    data_od: date | None = Query(default=None),
    data_do: date | None = Query(default=None),
    faktura_powiazana_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return magazyn_service.lista_dokumentow_magazynowych(
        db, skip, limit, typ, magazyn_id, data_od, data_do, faktura_powiazana_id
    )


@router.get(
    "/dokumenty-magazynowe/{dokument_id}", response_model=DokumentMagazynowyOut
)
def szczegoly_dokumentu_magazynowego(
    dokument_id: int, db: Session = Depends(get_db)
):
    return magazyn_service.pobierz_dokument_magazynowy(db, dokument_id)


@router.put(
    "/dokumenty-magazynowe/{dokument_id}",
    response_model=UtworzenieDokumentuMagazynowegoOut,
)
def aktualizuj_dokument_magazynowy(
    dokument_id: int, dane: DokumentMagazynowyUpdate, db: Session = Depends(get_db)
):
    dokument, ostrzezenia = magazyn_service.aktualizuj_dokument_magazynowy(
        db, dokument_id, dane
    )
    return UtworzenieDokumentuMagazynowegoOut(dokument=dokument, ostrzezenia=ostrzezenia)


@router.post(
    "/dokumenty-magazynowe/{dokument_id}/zatwierdz",
    response_model=DokumentMagazynowyOut,
)
def zatwierdz_dokument_magazynowy(dokument_id: int, db: Session = Depends(get_db)):
    return magazyn_service.zatwierdz_dokument_magazynowy(db, dokument_id)


@router.get("/stany-magazynowe", response_model=list[StanMagazynowyOut])
def lista_stanow_magazynowych(
    magazyn_id: int | None = Query(default=None), db: Session = Depends(get_db)
):
    return magazyn_service.lista_stanow_magazynowych(db, magazyn_id)
