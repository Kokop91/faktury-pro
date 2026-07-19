from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class KosztRecznyCreate(BaseModel):
    data: date
    kwota_grosze: int = Field(gt=0)
    kategoria: str = Field(min_length=1, max_length=100)
    opis: str | None = Field(default=None, max_length=1000)


class KosztRecznyUpdate(BaseModel):
    data: date | None = None
    kwota_grosze: int | None = Field(default=None, gt=0)
    kategoria: str | None = Field(default=None, min_length=1, max_length=100)
    opis: str | None = Field(default=None, max_length=1000)


class KosztRecznyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data: date
    kwota_grosze: int
    kategoria: str
    opis: str | None
    utworzono: datetime
    zaktualizowano: datetime
