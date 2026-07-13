from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PozycjaDokumentuMagazynowego(Base):
    __tablename__ = "pozycje_dokumentow_magazynowych"

    id: Mapped[int] = mapped_column(primary_key=True)
    dokument_id: Mapped[int] = mapped_column(
        ForeignKey("dokumenty_magazynowe.id"), nullable=False
    )
    produkt_id: Mapped[int] = mapped_column(ForeignKey("produkty.id"), nullable=False)

    ilosc: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    notatka: Mapped[str | None] = mapped_column(String(500))

    dokument: Mapped["DokumentMagazynowy"] = relationship(back_populates="pozycje")
    produkt: Mapped["Produkt"] = relationship()
