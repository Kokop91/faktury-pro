from sqlalchemy import Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LicznikNumeracjiInwentaryzacji(Base):
    """Licznik ostatniego uzytego numeru spisu inwentaryzacyjnego w danym roku
    (ciaglosc bez dziur) - jeden wspolny rejestr, mirror LicznikNumeracji faktur
    (w odroznieniu od LicznikNumeracjiMagazynowej, ktora ma osobna numeracje per
    typ dokumentu - inwentaryzacja ma tylko jeden "typ")."""

    __tablename__ = "liczniki_numeracji_inwentaryzacji"
    __table_args__ = (
        UniqueConstraint("rok", name="uq_liczniki_numeracji_inwentaryzacji_rok"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rok: Mapped[int] = mapped_column(Integer, nullable=False)
    ostatni_numer: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
