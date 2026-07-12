from sqlalchemy import Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LicznikNumeracji(Base):
    """Licznik ostatniego uzytego numeru faktury w danym roku (ciaglosc bez dziur)."""

    __tablename__ = "liczniki_numeracji"
    __table_args__ = (UniqueConstraint("rok", name="uq_liczniki_numeracji_rok"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rok: Mapped[int] = mapped_column(Integer, nullable=False)
    ostatni_numer: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
