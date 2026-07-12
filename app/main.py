from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import faktury, klienci
from app.database import get_db

app = FastAPI(title="Faktury Pro")

app.include_router(klienci.router)
app.include_router(faktury.router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
