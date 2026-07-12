from fastapi import FastAPI

from app.api import faktury, klienci

app = FastAPI(title="Faktury Pro")

app.include_router(klienci.router)
app.include_router(faktury.router)
