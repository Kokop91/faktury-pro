from datetime import datetime

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import TypPrzypomnienia


class PrzypomnieniePlatnosci(Base):
    """Historia wyslanych przypomnien o platnosci (Faza 23) - kazdy wiersz to
    JEDNO faktycznie wyslane przypomnienie. UniqueConstraint(faktura_id, typ)
    jest tym, co gwarantuje "to samo przypomnienie nie zostanie wyslane dwa
    razy" - niezaleznie od tego, ile razy appka sprawdzi kandydatow przy
    starcie (patrz app/services/przypomnienia_service.py:znajdz_kandydatow,
    ktora pomija fakturę/typ juz obecne w tej tabeli)."""

    __tablename__ = "przypomnienia_platnosci"
    __table_args__ = (UniqueConstraint("faktura_id", "typ", name="uq_przypomnienie_faktura_typ"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    faktura_id: Mapped[int] = mapped_column(ForeignKey("faktury.id"), nullable=False)

    typ: Mapped[TypPrzypomnienia] = mapped_column(
        Enum(TypPrzypomnienia, name="typ_przypomnienia"), nullable=False
    )
    adres_email: Mapped[str] = mapped_column(String(255), nullable=False)

    wyslano_o: Mapped[datetime] = mapped_column(server_default=func.now())

    faktura: Mapped["Faktura"] = relationship()
