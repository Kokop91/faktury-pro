from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.integracje import (
    GusPodmiotOut,
    KursWalutyOut,
    UstawieniaGusIn,
    UstawieniaGusOut,
)
from app.schemas.weryfikacja_bialej_listy import (
    SprawdzBialaListeIn,
    WeryfikacjaBialejListyOut,
)
from app.services import biala_lista_service, gus_service, integracje_ustawienia, nbp_service

router = APIRouter(prefix="/integracje", tags=["integracje"])


@router.get("/gus/ustawienia", response_model=UstawieniaGusOut)
def pobierz_ustawienia_gus():
    return integracje_ustawienia.wczytaj_ustawienia_gus()


@router.put("/gus/ustawienia", response_model=UstawieniaGusOut)
def zapisz_ustawienia_gus(dane: UstawieniaGusIn):
    zmiany = dane.model_dump(exclude_unset=True)
    try:
        return integracje_ustawienia.zapisz_ustawienia_gus(zmiany)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/gus/szukaj", response_model=GusPodmiotOut)
def szukaj_w_gus(nip: str = Query(min_length=10, max_length=10)):
    podmiot = gus_service.szukaj_po_nip(nip)
    if podmiot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nie znaleziono podmiotu o NIP {nip} w rejestrze REGON.",
        )
    return podmiot


@router.get("/nbp/kurs", response_model=KursWalutyOut)
def pobierz_kurs_nbp(
    waluta: str = Query(min_length=3, max_length=3),
    data_wystawienia: date = Query(),
):
    kurs, data_efektywna = nbp_service.pobierz_kurs_przed_data(waluta, data_wystawienia)
    return KursWalutyOut(waluta=waluta.upper(), kurs=str(kurs), data_efektywna=data_efektywna)


@router.post("/biala-lista/sprawdz", response_model=WeryfikacjaBialejListyOut)
def sprawdz_biala_liste(dane: SprawdzBialaListeIn, db: Session = Depends(get_db)):
    return biala_lista_service.sprawdz_nip(
        db,
        nip=dane.nip,
        numer_konta=dane.numer_konta,
        klient_id=dane.klient_id,
        faktura_id=dane.faktura_id,
    )


@router.get(
    "/biala-lista/klient/{klient_id}", response_model=list[WeryfikacjaBialejListyOut]
)
def historia_bialej_listy_klienta(klient_id: int, db: Session = Depends(get_db)):
    return biala_lista_service.historia_klienta(db, klient_id)


@router.get(
    "/biala-lista/faktura/{faktura_id}", response_model=list[WeryfikacjaBialejListyOut]
)
def historia_bialej_listy_faktury(faktura_id: int, db: Session = Depends(get_db)):
    return biala_lista_service.historia_faktury(db, faktura_id)
