from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PozycjaInwentaryzacji(Base):
    __tablename__ = "pozycje_inwentaryzacji"
    __table_args__ = (
        UniqueConstraint(
            "inwentaryzacja_id",
            "produkt_id",
            name="uq_pozycje_inwentaryzacji_inwentaryzacja_produkt",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inwentaryzacja_id: Mapped[int] = mapped_column(
        ForeignKey("inwentaryzacje.id"), nullable=False
    )
    produkt_id: Mapped[int] = mapped_column(ForeignKey("produkty.id"), nullable=False)

    # Stan zapisany w momencie otwarcia spisu (migawka) - punkt odniesienia do
    # wyliczenia roznicy przy zamknieciu, niezalezny od tego, co dzieje sie ze
    # StanMagazynowy w miedzyczasie.
    stan_systemowy: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    # Wpisywany stopniowo przez uzytkownika w trakcie liczenia - None dopoki
    # produkt nie zostal jeszcze policzony.
    stan_faktyczny: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)

    inwentaryzacja: Mapped["Inwentaryzacja"] = relationship(back_populates="pozycje")
    produkt: Mapped["Produkt"] = relationship()
