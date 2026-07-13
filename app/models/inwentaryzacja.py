from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StatusInwentaryzacji


class Inwentaryzacja(Base):
    __tablename__ = "inwentaryzacje"

    id: Mapped[int] = mapped_column(primary_key=True)
    magazyn_id: Mapped[int] = mapped_column(ForeignKey("magazyny.id"), nullable=False)

    numer: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    data_rozpoczecia: Mapped[date] = mapped_column(Date, nullable=False)
    data_zakonczenia: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[StatusInwentaryzacji] = mapped_column(
        Enum(StatusInwentaryzacji, name="status_inwentaryzacji"),
        nullable=False,
        default=StatusInwentaryzacji.W_TRAKCIE,
    )

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    pozycje: Mapped[list["PozycjaInwentaryzacji"]] = relationship(
        back_populates="inwentaryzacja", cascade="all, delete-orphan"
    )
