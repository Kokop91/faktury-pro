from sqlalchemy import Enum, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.enums import TypDokumentuMagazynowego


class LicznikNumeracjiMagazynowej(Base):
    """Licznik ostatniego uzytego numeru dokumentu magazynowego, osobny dla kazdego
    typu (PZ/WZ/PW/RW/MM) i roku (ciaglosc bez dziur w ramach typu+roku) - w
    odroznieniu od LicznikNumeracji faktur, ktory ma jeden wspolny rejestr na rok.
    """

    __tablename__ = "liczniki_numeracji_magazynowej"
    __table_args__ = (
        UniqueConstraint(
            "typ", "rok", name="uq_liczniki_numeracji_magazynowej_typ_rok"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    typ: Mapped[TypDokumentuMagazynowego] = mapped_column(
        Enum(TypDokumentuMagazynowego, name="typ_dokumentu_magazynowego"),
        nullable=False,
    )
    rok: Mapped[int] = mapped_column(Integer, nullable=False)
    ostatni_numer: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
