from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class WeryfikacjaBialejListy(Base):
    """Historia sprawdzen w wykazie podatnikow VAT (bialej liscie, API MF) -
    Faza 14. Kazde sprawdzenie zapisywane jako osobny wpis (nie nadpisywane),
    bo ma znaczenie dowodowe przy kontroli skarbowej: trzeba umiec wykazac
    CO i KIEDY bylo sprawdzone, nie tylko ostatni stan.

    Dwa konteksty uzycia (rozroznione tym, ktore z klient_id/kontekst_firmy
    jest wypelnione):
    - przy kliencie: sam NIP, bez numeru konta (weryfikacja statusu VAT kontrahenta)
    - przy fakturze: NIP i numer konta WLASNEJ firmy (Firma.nip/bank_numer_konta)
      wydrukowane na tej konkretnej fakturze - potwierdzenie, ze konto do
      wplaty bylo poprawnie zarejestrowane w dniu wystawienia.
    """

    __tablename__ = "weryfikacje_bialej_listy"

    id: Mapped[int] = mapped_column(primary_key=True)

    klient_id: Mapped[int | None] = mapped_column(
        ForeignKey("klienci.id"), nullable=True
    )
    faktura_id: Mapped[int | None] = mapped_column(
        ForeignKey("faktury.id"), nullable=True
    )

    nip: Mapped[str] = mapped_column(String(10), nullable=False)
    numer_konta: Mapped[str | None] = mapped_column(String(34), nullable=True)
    data_na_dzien: Mapped[date] = mapped_column(Date, nullable=False)

    znaleziono: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_vat: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nazwa_podmiotu: Mapped[str | None] = mapped_column(String(255), nullable=True)
    konto_zgodne: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    sprawdzono_o: Mapped[datetime] = mapped_column(server_default=func.now())

    klient: Mapped["Klient | None"] = relationship()
    faktura: Mapped["Faktura | None"] = relationship()
