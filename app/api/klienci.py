from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.klient import (
    KlientCreate,
    KlientImportWiersz,
    KlientImportWynik,
    KlientOut,
    KlientUpdate,
)
from app.services import klienci as klienci_service

router = APIRouter(prefix="/klienci", tags=["klienci"])


@router.post("", response_model=KlientOut, status_code=201)
def dodaj_klienta(dane: KlientCreate, db: Session = Depends(get_db)):
    return klienci_service.utworz_klienta(db, dane)


@router.post("/import/podglad", response_model=list[KlientImportWynik])
def podglad_importu_klientow(
    wiersze: list[KlientImportWiersz], db: Session = Depends(get_db)
):
    """Walidacja "sucha" (Faza 26) - identyczna logika co faktyczny import,
    ale niczego nie zapisuje. Wywolywane z kroku podgladu w GUI PRZED
    kliknieciem "Importuj"."""
    return klienci_service.importuj_klientow(db, wiersze, zapisz=False)


@router.post("/import", response_model=list[KlientImportWynik])
def importuj_klientow(wiersze: list[KlientImportWiersz], db: Session = Depends(get_db)):
    return klienci_service.importuj_klientow(db, wiersze, zapisz=True)


@router.get("", response_model=list[KlientOut])
def lista_klientow(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    tylko_aktywni: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    return klienci_service.lista_klientow(db, skip, limit, tylko_aktywni)


@router.get("/{klient_id}", response_model=KlientOut)
def szczegoly_klienta(klient_id: int, db: Session = Depends(get_db)):
    return klienci_service.pobierz_klienta(db, klient_id)


@router.put("/{klient_id}", response_model=KlientOut)
def edytuj_klienta(klient_id: int, dane: KlientUpdate, db: Session = Depends(get_db)):
    return klienci_service.aktualizuj_klienta(db, klient_id, dane)


@router.delete("/{klient_id}", status_code=204)
def usun_klienta(klient_id: int, db: Session = Depends(get_db)):
    klienci_service.usun_klienta(db, klient_id)
