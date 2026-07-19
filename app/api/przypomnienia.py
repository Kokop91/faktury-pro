from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.przypomnienia import (
    KandydatPrzypomnieniaOut,
    WynikWyslaniaPrzypomnieniaOut,
    WyslijPrzypomnieniaIn,
)
from app.services import przypomnienia_service

router = APIRouter(prefix="/przypomnienia", tags=["przypomnienia"])


@router.get("/do-wyslania", response_model=list[KandydatPrzypomnieniaOut])
def do_wyslania(db: Session = Depends(get_db)):
    return przypomnienia_service.znajdz_kandydatow(db)


@router.post("/wyslij", response_model=list[WynikWyslaniaPrzypomnieniaOut])
def wyslij(dane: WyslijPrzypomnieniaIn, db: Session = Depends(get_db)):
    return przypomnienia_service.wyslij_przypomnienia(db, dane.pozycje)
