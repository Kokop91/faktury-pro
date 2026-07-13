from datetime import date, datetime

from sqlalchemy import BigInteger, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class PlatnoscFaktury(Base):
    __tablename__ = "platnosci_faktury"

    id: Mapped[int] = mapped_column(primary_key=True)
    faktura_id: Mapped[int] = mapped_column(
        ForeignKey("faktury.id"), nullable=False, index=True
    )

    data_platnosci: Mapped[date] = mapped_column(Date, nullable=False)
    kwota_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    notatka: Mapped[str | None] = mapped_column(String(500), nullable=True)

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())

    faktura: Mapped["Faktura"] = relationship(back_populates="platnosci")
