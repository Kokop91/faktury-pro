from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
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
    # Opcjonalne, sensowne wylacznie na PZ (nie wymuszane przez baze/schemat -
    # patrz app/services/rentownosc_service.py, ktore agreguje je TYLKO dla
    # typ=PZ). Dodatkowe, uzupelniajace zrodlo kosztow dla marzy okresu obok
    # DokumentKosztowy/KosztReczny - None = appka nie zna ceny zakupu tej
    # konkretnej dostawy, pomijane w agregacji, nigdy traktowane jako 0.
    cena_zakupu_netto_grosze: Mapped[int | None] = mapped_column(Integer)

    dokument: Mapped["DokumentMagazynowy"] = relationship(back_populates="pozycje")
    produkt: Mapped["Produkt"] = relationship()
