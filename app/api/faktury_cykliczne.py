from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.faktura import FakturaOut
from app.schemas.szablon_cykliczny import (
    SzablonCyklicznyCreate,
    SzablonCyklicznyOut,
    SzablonCyklicznyStatusUpdate,
    SzablonCyklicznyUpdate,
    WygenerujFakturyCyklicznieIn,
    ZaleglaFakturaCykliczna,
)
from app.services import faktury_cykliczne as cykliczne_service
from app.services import platnosci as platnosci_service

router = APIRouter(prefix="/faktury-cykliczne", tags=["faktury-cykliczne"])


@router.post("", response_model=SzablonCyklicznyOut, status_code=201)
def utworz_szablon(dane: SzablonCyklicznyCreate, db: Session = Depends(get_db)):
    szablon = cykliczne_service.utworz_szablon(db, dane)
    return cykliczne_service.zbuduj_szablon_out(db, szablon)


@router.get("", response_model=list[SzablonCyklicznyOut])
def lista_szablonow(
    tylko_aktywne: bool = Query(default=False), db: Session = Depends(get_db)
):
    szablony = cykliczne_service.lista_szablonow(db, tylko_aktywne)
    return [cykliczne_service.zbuduj_szablon_out(db, s) for s in szablony]


# Musi byc zadeklarowane PRZED "/{szablon_id}" - patrz analogiczny komentarz
# przy GET /faktury/naleznosci w app/api/faktury.py.
@router.get("/zalegle", response_model=list[ZaleglaFakturaCykliczna])
def zalegle_faktury_cykliczne(db: Session = Depends(get_db)):
    return cykliczne_service.znajdz_zalegle(db)


@router.post("/generuj", response_model=list[FakturaOut])
def generuj_faktury_cykliczne(
    dane: WygenerujFakturyCyklicznieIn, db: Session = Depends(get_db)
):
    wybory = (
        [(p.szablon_id, p.okres) for p in dane.pozycje]
        if dane.pozycje is not None
        else None
    )
    faktury = cykliczne_service.generuj_faktury(db, wybory)
    return [platnosci_service.zbuduj_fakture_out(f) for f in faktury]


@router.get("/{szablon_id}", response_model=SzablonCyklicznyOut)
def szczegoly_szablonu(szablon_id: int, db: Session = Depends(get_db)):
    szablon = cykliczne_service.pobierz_szablon(db, szablon_id)
    return cykliczne_service.zbuduj_szablon_out(db, szablon)


@router.put("/{szablon_id}", response_model=SzablonCyklicznyOut)
def edytuj_szablon(
    szablon_id: int, dane: SzablonCyklicznyUpdate, db: Session = Depends(get_db)
):
    szablon = cykliczne_service.aktualizuj_szablon(db, szablon_id, dane)
    return cykliczne_service.zbuduj_szablon_out(db, szablon)


@router.patch("/{szablon_id}/status", response_model=SzablonCyklicznyOut)
def zmien_status_szablonu(
    szablon_id: int, dane: SzablonCyklicznyStatusUpdate, db: Session = Depends(get_db)
):
    szablon = cykliczne_service.zmien_status_szablonu(db, szablon_id, dane.status)
    return cykliczne_service.zbuduj_szablon_out(db, szablon)


@router.get("/{szablon_id}/faktury", response_model=list[FakturaOut])
def historia_faktur_szablonu(szablon_id: int, db: Session = Depends(get_db)):
    faktury = cykliczne_service.historia_faktur_szablonu(db, szablon_id)
    return [platnosci_service.zbuduj_fakture_out(f) for f in faktury]
