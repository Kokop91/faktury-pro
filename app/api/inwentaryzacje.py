from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.enums import StatusInwentaryzacji
from app.schemas.inwentaryzacja import (
    AktualizacjaPozycjiInwentaryzacji,
    InwentaryzacjaCreate,
    InwentaryzacjaListOut,
    InwentaryzacjaOut,
    ZamkniecieInwentaryzacjiOut,
)
from app.services import inwentaryzacja_service

router = APIRouter(prefix="/inwentaryzacje", tags=["magazyn"])


@router.post("", response_model=InwentaryzacjaOut, status_code=201)
def otworz_inwentaryzacje(dane: InwentaryzacjaCreate, db: Session = Depends(get_db)):
    inwentaryzacja = inwentaryzacja_service.otworz_inwentaryzacje(db, dane)
    return inwentaryzacja_service.zbuduj_inwentaryzacja_out(inwentaryzacja)


@router.get("", response_model=list[InwentaryzacjaListOut])
def lista_inwentaryzacji(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    magazyn_id: int | None = Query(default=None),
    status: StatusInwentaryzacji | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return inwentaryzacja_service.lista_inwentaryzacji(
        db, magazyn_id, status, skip, limit
    )


@router.get("/{inwentaryzacja_id}", response_model=InwentaryzacjaOut)
def szczegoly_inwentaryzacji(inwentaryzacja_id: int, db: Session = Depends(get_db)):
    inwentaryzacja = inwentaryzacja_service.pobierz_inwentaryzacje(
        db, inwentaryzacja_id
    )
    return inwentaryzacja_service.zbuduj_inwentaryzacja_out(inwentaryzacja)


@router.put("/{inwentaryzacja_id}/pozycje", response_model=InwentaryzacjaOut)
def zapisz_pozycje(
    inwentaryzacja_id: int,
    dane: AktualizacjaPozycjiInwentaryzacji,
    db: Session = Depends(get_db),
):
    inwentaryzacja = inwentaryzacja_service.zapisz_pozycje(
        db, inwentaryzacja_id, dane
    )
    return inwentaryzacja_service.zbuduj_inwentaryzacja_out(inwentaryzacja)


@router.post("/{inwentaryzacja_id}/zamknij", response_model=ZamkniecieInwentaryzacjiOut)
def zamknij_inwentaryzacje(inwentaryzacja_id: int, db: Session = Depends(get_db)):
    inwentaryzacja, dokumenty, ostrzezenia = inwentaryzacja_service.zamknij_inwentaryzacje(
        db, inwentaryzacja_id
    )
    return ZamkniecieInwentaryzacjiOut(
        inwentaryzacja=inwentaryzacja_service.zbuduj_inwentaryzacja_out(inwentaryzacja),
        dokumenty_utworzone=dokumenty,
        ostrzezenia=ostrzezenia,
    )
