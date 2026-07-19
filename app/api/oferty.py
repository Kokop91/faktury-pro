from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import StatusOferty
from app.schemas.faktura import FakturaOut
from app.schemas.oferta import (
    OfertaCreate,
    OfertaOut,
    OfertaStatusUpdate,
    OfertaUpdate,
)
from app.services import oferty as oferty_service
from app.services import pdf as pdf_service
from app.services import platnosci as platnosci_service

router = APIRouter(prefix="/oferty", tags=["oferty"])


@router.post("", response_model=OfertaOut, status_code=201)
def utworz_oferte(dane: OfertaCreate, db: Session = Depends(get_db)):
    oferta = oferty_service.utworz_oferte(db, dane)
    return oferty_service.zbuduj_oferte_out(oferta)


@router.get("", response_model=list[OfertaOut])
def lista_ofert(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: StatusOferty | None = Query(default=None),
    klient_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    oferty = oferty_service.lista_ofert(db, skip, limit, status, klient_id)
    return [oferty_service.zbuduj_oferte_out(o) for o in oferty]


@router.get("/{oferta_id}", response_model=OfertaOut)
def szczegoly_oferty(oferta_id: int, db: Session = Depends(get_db)):
    oferta = oferty_service.pobierz_oferte(db, oferta_id)
    return oferty_service.zbuduj_oferte_out(oferta)


@router.put("/{oferta_id}", response_model=OfertaOut)
def edytuj_oferte(oferta_id: int, dane: OfertaUpdate, db: Session = Depends(get_db)):
    oferta = oferty_service.aktualizuj_oferte(db, oferta_id, dane)
    return oferty_service.zbuduj_oferte_out(oferta)


@router.patch("/{oferta_id}/status", response_model=OfertaOut)
def zmien_status_oferty(
    oferta_id: int, dane: OfertaStatusUpdate, db: Session = Depends(get_db)
):
    oferta = oferty_service.zmien_status_oferty(db, oferta_id, dane.status)
    return oferty_service.zbuduj_oferte_out(oferta)


@router.post("/{oferta_id}/wystaw-fakture", response_model=FakturaOut, status_code=201)
def wystaw_fakture_z_oferty(oferta_id: int, db: Session = Depends(get_db)):
    faktura = oferty_service.wystaw_fakture_z_oferty(db, oferta_id)
    return platnosci_service.zbuduj_fakture_out(faktura)


@router.get("/{oferta_id}/pdf")
def pobierz_pdf_oferty(oferta_id: int, db: Session = Depends(get_db)):
    pdf_bytes, numer = pdf_service.generuj_pdf_oferty(db, oferta_id)
    nazwa_pliku = numer.replace("/", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="oferta_{nazwa_pliku}.pdf"'
        },
    )
