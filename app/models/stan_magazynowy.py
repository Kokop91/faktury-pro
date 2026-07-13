from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StanMagazynowy(Base):
    __tablename__ = "stany_magazynowe"
    __table_args__ = (
        UniqueConstraint(
            "produkt_id", "magazyn_id", name="uq_stany_magazynowe_produkt_magazyn"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    produkt_id: Mapped[int] = mapped_column(ForeignKey("produkty.id"), nullable=False)
    magazyn_id: Mapped[int] = mapped_column(ForeignKey("magazyny.id"), nullable=False)

    ilosc: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("0")
    )
    # Prog alertu (opcjonalny) - ponizej tej ilosci towar ma byc zglaszany jako
    # brakujacy w raportach magazynowych (Faza 8/3.7 planu).
    stan_minimalny: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))

    produkt: Mapped["Produkt"] = relationship(back_populates="stany_magazynowe")
    magazyn: Mapped["Magazyn"] = relationship(back_populates="stany_magazynowe")
