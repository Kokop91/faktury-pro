from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import StawkaVat


class Produkt(Base):
    __tablename__ = "produkty"

    id: Mapped[int] = mapped_column(primary_key=True)
    firma_id: Mapped[int] = mapped_column(ForeignKey("firmy.id"), nullable=False)

    nazwa: Mapped[str] = mapped_column(String(255), nullable=False)
    jednostka_miary: Mapped[str] = mapped_column(String(20), nullable=False)
    cena_netto_grosze: Mapped[int] = mapped_column(BigInteger, nullable=False)
    domyslna_stawka_vat: Mapped[StawkaVat] = mapped_column(
        Enum(StawkaVat, name="stawka_vat"),
        nullable=False,
        default=StawkaVat.STAWKA_23,
    )

    # Towar magazynowy (ma stan, przechodzi przez dokumenty magazynowe) vs usluga
    # (bez stanu) - patrz CLAUDE.md, regula 5. Uslugi nigdy nie maja wierszy
    # w stany_magazynowe ani pozycji w dokumentach magazynowych.
    jest_magazynowy: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Faza 21 (split payment) - swiadomy wybor uzytkownika przy tworzeniu
    # produktu: appka nie moze sama wiedziec, ze dany towar/usluga jest
    # "wyrobem stalowym" czy inna pozycja z zalacznika nr 15 do ustawy o VAT
    # bez informacji od czlowieka. Uzywane do automatycznego wykrywania
    # obowiazku MPP na fakturze (app/services/mpp_service.py) przez
    # dopasowanie PozycjaFaktury.nazwa po tekscie (ten sam wzorzec co
    # dopasowanie WZ z Fazy 19 - PozycjaFaktury nie ma FK do Produkt).
    objety_zalacznikiem_15: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    aktywny: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    utworzono: Mapped[datetime] = mapped_column(server_default=func.now())
    zaktualizowano: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    firma: Mapped["Firma"] = relationship(back_populates="produkty")
    stany_magazynowe: Mapped[list["StanMagazynowy"]] = relationship(
        back_populates="produkt"
    )
