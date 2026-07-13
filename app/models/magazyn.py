from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Magazyn(Base):
    __tablename__ = "magazyny"

    id: Mapped[int] = mapped_column(primary_key=True)
    firma_id: Mapped[int] = mapped_column(ForeignKey("firmy.id"), nullable=False)

    nazwa: Mapped[str] = mapped_column(String(255), nullable=False)
    lokalizacja: Mapped[str | None] = mapped_column(String(500))

    aktywny: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    firma: Mapped["Firma"] = relationship(back_populates="magazyny")
    stany_magazynowe: Mapped[list["StanMagazynowy"]] = relationship(
        back_populates="magazyn"
    )
