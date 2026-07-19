from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import (
    dashboard,
    dokumenty_kosztowe,
    email,
    faktury,
    faktury_cykliczne,
    firma,
    integracje,
    inwentaryzacje,
    klienci,
    koszty_reczne,
    ksef,
    magazyn,
    magazyny,
    oferty,
    produkty,
    przypomnienia,
    raporty,
    rentownosc,
)
from app.database import get_db

app = FastAPI(title="Faktury Pro")

app.include_router(klienci.router)
app.include_router(faktury.router)
app.include_router(faktury_cykliczne.router)
app.include_router(oferty.router)
app.include_router(produkty.router)
app.include_router(magazyny.router)
app.include_router(magazyn.router)
app.include_router(inwentaryzacje.router)
app.include_router(raporty.router)
app.include_router(dashboard.router)
app.include_router(firma.router)
app.include_router(integracje.router)
app.include_router(ksef.router)
app.include_router(dokumenty_kosztowe.router)
app.include_router(koszty_reczne.router)
app.include_router(rentownosc.router)
app.include_router(email.router)
app.include_router(przypomnienia.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
