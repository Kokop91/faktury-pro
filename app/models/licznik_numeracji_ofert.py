from sqlalchemy import Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LicznikNumeracjiOfert(Base):
    """Licznik ostatniego uzytego numeru oferty w danym roku (ciaglosc bez
    dziur) - jeden wspolny rejestr, mirror LicznikNumeracji faktur/
    LicznikNumeracjiInwentaryzacji (oferta ma tylko jeden "typ", w
    odroznieniu od LicznikNumeracjiMagazynowej)."""

    __tablename__ = "liczniki_numeracji_ofert"
    __table_args__ = (
        UniqueConstraint("rok", name="uq_liczniki_numeracji_ofert_rok"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rok: Mapped[int] = mapped_column(Integer, nullable=False)
    ostatni_numer: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
