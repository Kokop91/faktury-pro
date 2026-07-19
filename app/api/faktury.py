from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import StatusFaktury
from app.schemas.faktura import (
    FakturaCreate,
    FakturaOut,
    FakturaStatusUpdate,
    FakturaUpdate,
    NaleznosciOut,
    PlatnoscCreate,
    PlatnoscOut,
    WyslijKsefOut,
    WyslijKsefZbiorczoWynikOut,
    WyslijZbiorczoIn,
)
from app.schemas.przypomnienia import PrzypomnieniePlatnosciOut
from app.services import faktury as faktury_service
from app.services import ksef_service
from app.services import pdf as pdf_service
from app.services import platnosci as platnosci_service
from app.services import przypomnienia_service

router = APIRouter(prefix="/faktury", tags=["faktury"])


@router.post("", response_model=FakturaOut, status_code=201)
def utworz_fakture(dane: FakturaCreate, db: Session = Depends(get_db)):
    faktura = faktury_service.utworz_fakture(db, dane)
    return platnosci_service.zbuduj_fakture_out(faktura)


@router.get("", response_model=list[FakturaOut])
def lista_faktur(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: StatusFaktury | None = Query(default=None),
    klient_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    faktury = faktury_service.lista_faktur(db, skip, limit, status, klient_id)
    return [platnosci_service.zbuduj_fakture_out(f) for f in faktury]


# Musi byc zadeklarowane PRZED "/{faktura_id}" - inaczej Starlette dopasuje
# "/faktury/naleznosci" do wzorca "/faktury/{faktura_id}" i zwroci 422 (proba
# konwersji "naleznosci" na int), zamiast dojsc do tego endpointu.
@router.get("/naleznosci", response_model=NaleznosciOut)
def naleznosci(db: Session = Depends(get_db)):
    faktury, suma_grosze = platnosci_service.lista_naleznosci(db)
    return NaleznosciOut(
        suma_naleznosci_grosze=suma_grosze,
        faktury=[platnosci_service.zbuduj_fakture_out(f) for f in faktury],
    )


@router.post("/ksef/wyslij-zbiorczo", response_model=list[WyslijKsefZbiorczoWynikOut])
def wyslij_faktury_zbiorczo(dane: WyslijZbiorczoIn, db: Session = Depends(get_db)):
    return ksef_service.wyslij_faktury_zbiorczo(db, dane.faktura_ids)


@router.get("/{faktura_id}", response_model=FakturaOut)
def szczegoly_faktury(faktura_id: int, db: Session = Depends(get_db)):
    faktura = faktury_service.pobierz_fakture(db, faktura_id)
    return platnosci_service.zbuduj_fakture_out(faktura)


@router.get("/{faktura_id}/platnosci", response_model=list[PlatnoscOut])
def lista_platnosci_faktury(faktura_id: int, db: Session = Depends(get_db)):
    return platnosci_service.pobierz_platnosci_faktury(db, faktura_id)


@router.get("/{faktura_id}/przypomnienia", response_model=list[PrzypomnieniePlatnosciOut])
def historia_przypomnien_faktury(faktura_id: int, db: Session = Depends(get_db)):
    return przypomnienia_service.historia_faktury(db, faktura_id)


@router.post(
    "/{faktura_id}/platnosci", response_model=PlatnoscOut, status_code=201
)
def dodaj_platnosc(
    faktura_id: int, dane: PlatnoscCreate, db: Session = Depends(get_db)
):
    return platnosci_service.dodaj_platnosc(db, faktura_id, dane)


@router.get("/{faktura_id}/pdf")
def pobierz_pdf_faktury(faktura_id: int, db: Session = Depends(get_db)):
    pdf_bytes, numer = pdf_service.generuj_pdf_faktury(db, faktura_id)
    nazwa_pliku = numer.replace("/", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="faktura_{nazwa_pliku}.pdf"'
        },
    )


@router.put("/{faktura_id}", response_model=FakturaOut)
def edytuj_fakture(
    faktura_id: int, dane: FakturaUpdate, db: Session = Depends(get_db)
):
    faktura = faktury_service.aktualizuj_fakture(db, faktura_id, dane)
    return platnosci_service.zbuduj_fakture_out(faktura)


@router.patch("/{faktura_id}/status", response_model=FakturaOut)
def zmien_status_faktury(
    faktura_id: int, dane: FakturaStatusUpdate, db: Session = Depends(get_db)
):
    faktura = faktury_service.zmien_status_faktury(db, faktura_id, dane.status)
    return platnosci_service.zbuduj_fakture_out(faktura)


@router.post("/{faktura_id}/ksef/wyslij", response_model=WyslijKsefOut)
def wyslij_fakture_do_ksef(faktura_id: int, db: Session = Depends(get_db)):
    return ksef_service.wyslij_fakture_do_ksef(db, faktura_id)


@router.get("/{faktura_id}/ksef/upo")
def pobierz_upo_faktury(faktura_id: int, db: Session = Depends(get_db)):
    faktura = faktury_service.pobierz_fakture(db, faktura_id)
    if not faktura.upo_xml:
        raise HTTPException(status_code=404, detail="UPO dla tej faktury nie jest jeszcze dostępne.")
    nazwa_pliku = faktura.numer.replace("/", "_")
    return Response(
        content=faktura.upo_xml.encode("utf-8"),
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="upo_{nazwa_pliku}.xml"'
        },
    )
