from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Klient(Base):
    __tablename__ = "klienci"

    id: Mapped[int] = mapped_column(primary_key=True)
    firma_id: Mapped[int] = mapped_column(ForeignKey("firmy.id"), nullable=False)

    nazwa: Mapped[str] = mapped_column(String(255), nullable=False)
    nip: Mapped[str | None] = mapped_column(String(10))

    ulica: Mapped[str | None] = mapped_column(String(255))
    kod_pocztowy: Mapped[str | None] = mapped_column(String(10))
    miejscowosc: Mapped[str | None] = mapped_column(String(255))
    kraj: Mapped[str] = mapped_column(String(100), nullable=False, default="Polska")

    email: Mapped[str | None] = mapped_column(String(255))
    telefon: Mapped[str | None] = mapped_column(String(30))

    domyslna_waluta: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    domyslny_termin_platnosci_dni: Mapped[int] = mapped_column(
        Integer, nullable=False, default=14
    )

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    firma: Mapped["Firma"] = relationship(back_populates="klienci")
    faktury: Mapped[list["Faktura"]] = relationship(back_populates="klient")
