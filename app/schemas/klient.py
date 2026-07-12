import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

NIP_REGEX = re.compile(r"^\d{10}$")


def waliduj_nip(nip: str | None) -> str | None:
    if nip is not None and not NIP_REGEX.match(nip):
        raise ValueError("NIP musi się składać z dokładnie 10 cyfr")
    return nip


class KlientBase(BaseModel):
    nazwa: str = Field(min_length=1, max_length=255)
    nip: str | None = Field(default=None, max_length=10)
    ulica: str | None = Field(default=None, max_length=255)
    kod_pocztowy: str | None = Field(default=None, max_length=10)
    miejscowosc: str | None = Field(default=None, max_length=255)
    kraj: str = Field(default="Polska", max_length=100)
    email: str | None = Field(default=None, max_length=255)
    telefon: str | None = Field(default=None, max_length=30)
    domyslna_waluta: str = Field(default="PLN", min_length=3, max_length=3)
    domyslny_termin_platnosci_dni: int = Field(default=14, ge=0)

    _waliduj_nip = field_validator("nip")(waliduj_nip)


class KlientCreate(KlientBase):
    pass


class KlientUpdate(BaseModel):
    nazwa: str | None = Field(default=None, min_length=1, max_length=255)
    nip: str | None = Field(default=None, max_length=10)
    ulica: str | None = Field(default=None, max_length=255)
    kod_pocztowy: str | None = Field(default=None, max_length=10)
    miejscowosc: str | None = Field(default=None, max_length=255)
    kraj: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    telefon: str | None = Field(default=None, max_length=30)
    domyslna_waluta: str | None = Field(default=None, min_length=3, max_length=3)
    domyslny_termin_platnosci_dni: int | None = Field(default=None, ge=0)
    aktywny: bool | None = None

    _waliduj_nip = field_validator("nip")(waliduj_nip)


class KlientOut(KlientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    firma_id: int
    aktywny: bool
    utworzono: datetime
    zaktualizowano: datetime
