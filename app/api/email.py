from fastapi import APIRouter, HTTPException, status

from app.schemas.email import TestEmailOut, UstawieniaEmailIn, UstawieniaEmailOut
from app.services import email_service, email_ustawienia

router = APIRouter(prefix="/email", tags=["email"])


@router.get("/ustawienia", response_model=UstawieniaEmailOut)
def pobierz_ustawienia():
    return email_ustawienia.wczytaj_ustawienia_email()


@router.put("/ustawienia", response_model=UstawieniaEmailOut)
def zapisz_ustawienia(dane: UstawieniaEmailIn):
    zmiany = dane.model_dump(exclude_unset=True)
    try:
        return email_ustawienia.zapisz_ustawienia_email(zmiany)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/testuj-polaczenie", response_model=TestEmailOut)
def testuj_polaczenie():
    return email_service.testuj_polaczenie()
