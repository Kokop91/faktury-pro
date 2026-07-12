from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import StatusFaktury
from app.schemas.faktura import (
    FakturaCreate,
    FakturaOut,
    FakturaStatusUpdate,
    FakturaUpdate,
)
from app.services import faktury as faktury_service
from app.services import pdf as pdf_service

router = APIRouter(prefix="/faktury", tags=["faktury"])


@router.post("", response_model=FakturaOut, status_code=201)
def utworz_fakture(dane: FakturaCreate, db: Session = Depends(get_db)):
    return faktury_service.utworz_fakture(db, dane)


@router.get("", response_model=list[FakturaOut])
def lista_faktur(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status: StatusFaktury | None = Query(default=None),
    klient_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return faktury_service.lista_faktur(db, skip, limit, status, klient_id)


@router.get("/{faktura_id}", response_model=FakturaOut)
def szczegoly_faktury(faktura_id: int, db: Session = Depends(get_db)):
    return faktury_service.pobierz_fakture(db, faktura_id)


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
    return faktury_service.aktualizuj_fakture(db, faktura_id, dane)


@router.patch("/{faktura_id}/status", response_model=FakturaOut)
def zmien_status_faktury(
    faktura_id: int, dane: FakturaStatusUpdate, db: Session = Depends(get_db)
):
    return faktury_service.zmien_status_faktury(db, faktura_id, dane.status)
