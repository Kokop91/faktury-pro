from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import StatusDokumentuKosztowego
from app.schemas.dokument_kosztowy import (
    DokumentKosztowyOut,
    DokumentKosztowyStatusUpdate,
    DokumentKosztowySzczegolyOut,
    LiczbaNowychOut,
)
from app.services import dokumenty_kosztowe_service

router = APIRouter(prefix="/dokumenty-kosztowe", tags=["dokumenty-kosztowe"])


@router.get("", response_model=list[DokumentKosztowyOut])
def lista_dokumentow(
    status: StatusDokumentuKosztowego | None = Query(default=None),
    data_od: date | None = Query(default=None),
    data_do: date | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return dokumenty_kosztowe_service.lista_dokumentow(db, status, data_od, data_do, skip, limit)


@router.get("/liczba-nowych", response_model=LiczbaNowychOut)
def liczba_nowych(db: Session = Depends(get_db)):
    return LiczbaNowychOut(liczba_nowych=dokumenty_kosztowe_service.liczba_nowych(db))


@router.get("/{dokument_id}", response_model=DokumentKosztowySzczegolyOut)
def szczegoly_dokumentu(dokument_id: int, db: Session = Depends(get_db)):
    return dokumenty_kosztowe_service.pobierz_dokument(db, dokument_id)


@router.patch("/{dokument_id}/status", response_model=DokumentKosztowyOut)
def zmien_status_dokumentu(
    dokument_id: int, dane: DokumentKosztowyStatusUpdate, db: Session = Depends(get_db)
):
    return dokumenty_kosztowe_service.zmien_status(db, dokument_id, dane.status)
