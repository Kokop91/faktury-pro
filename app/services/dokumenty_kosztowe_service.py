from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DokumentKosztowy, StatusDokumentuKosztowego


def lista_dokumentow(
    db: Session,
    status_filtr: StatusDokumentuKosztowego | None,
    data_od: date | None,
    data_do: date | None,
    skip: int,
    limit: int,
) -> list[DokumentKosztowy]:
    zapytanie = select(DokumentKosztowy)
    if status_filtr is not None:
        zapytanie = zapytanie.where(DokumentKosztowy.status == status_filtr)
    if data_od is not None:
        zapytanie = zapytanie.where(DokumentKosztowy.data_wystawienia >= data_od)
    if data_do is not None:
        zapytanie = zapytanie.where(DokumentKosztowy.data_wystawienia <= data_do)
    zapytanie = (
        zapytanie.order_by(DokumentKosztowy.data_wystawienia.desc(), DokumentKosztowy.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(zapytanie).scalars().all())


def liczba_nowych(db: Session) -> int:
    zapytanie = select(DokumentKosztowy).where(
        DokumentKosztowy.status == StatusDokumentuKosztowego.NOWA
    )
    return len(db.execute(zapytanie).scalars().all())


def pobierz_dokument(db: Session, dokument_id: int) -> DokumentKosztowy:
    dokument = db.get(DokumentKosztowy, dokument_id)
    if dokument is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono dokumentu kosztowego o podanym id.",
        )
    return dokument


def zmien_status(
    db: Session, dokument_id: int, nowy_status: StatusDokumentuKosztowego
) -> DokumentKosztowy:
    dokument = pobierz_dokument(db, dokument_id)
    dokument.status = nowy_status
    db.commit()
    db.refresh(dokument)
    return dokument
