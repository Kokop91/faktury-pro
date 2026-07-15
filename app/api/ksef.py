from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ksef import PobierzKosztyOut, TestKsefOut, UstawieniaKsefIn, UstawieniaKsefOut
from app.services import ksef_koszty_service, ksef_service, ksef_ustawienia

router = APIRouter(prefix="/ksef", tags=["ksef"])


@router.get("/ustawienia", response_model=UstawieniaKsefOut)
def pobierz_ustawienia():
    return ksef_ustawienia.wczytaj_ustawienia_ksef()


@router.put("/ustawienia", response_model=UstawieniaKsefOut)
def zapisz_ustawienia(dane: UstawieniaKsefIn):
    zmiany = dane.model_dump(exclude_unset=True)
    try:
        return ksef_ustawienia.zapisz_ustawienia_ksef(zmiany)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/testuj-polaczenie", response_model=TestKsefOut)
def testuj_polaczenie(db: Session = Depends(get_db)):
    return ksef_service.testuj_polaczenie(db)


@router.post("/pobierz-koszty", response_model=PobierzKosztyOut)
def pobierz_koszty(db: Session = Depends(get_db)):
    return ksef_koszty_service.pobierz_nowe_faktury_kosztowe(db)
