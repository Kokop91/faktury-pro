from datetime import datetime

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StawkaVat


class Firma(Base):
    __tablename__ = "firmy"

    id: Mapped[int] = mapped_column(primary_key=True)

    nazwa: Mapped[str] = mapped_column(String(255), nullable=False)
    nip: Mapped[str] = mapped_column(String(10), nullable=False, unique=True)

    ulica: Mapped[str | None] = mapped_column(String(255))
    kod_pocztowy: Mapped[str | None] = mapped_column(String(10))
    miejscowosc: Mapped[str | None] = mapped_column(String(255))
    kraj: Mapped[str] = mapped_column(String(100), nullable=False, default="Polska")

    email: Mapped[str | None] = mapped_column(String(255))
    telefon: Mapped[str | None] = mapped_column(String(30))

    bank_nazwa: Mapped[str | None] = mapped_column(String(255))
    bank_numer_konta: Mapped[str | None] = mapped_column(String(34))

    logo_path: Mapped[str | None] = mapped_column(String(500))

    domyslna_stawka_vat: Mapped[StawkaVat] = mapped_column(
        Enum(StawkaVat, name="stawka_vat"),
        nullable=False,
        default=StawkaVat.STAWKA_23,
    )

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    klienci: Mapped[list["Klient"]] = relationship(back_populates="firma")
