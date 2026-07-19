"""Przypomnienia o platnosciach (Faza 23, Etap 4) - pierwsze faktyczne uzycie
infrastruktury SMTP zbudowanej w tej samej fazie (app/services/email_service.py).

Trzy niezalezne rodzaje przypomnienia (TypPrzypomnienia), kazdy wlaczany
osobno w Ustawieniach (Firma.przypomnienia_*). Wykrywanie kandydatow uzywa
progu ">=" (nie "== dzisiaj dokladnie") - ten sam wzorzec "zalegle" co faktury
cykliczne z Fazy 15 (app/services/faktury_cykliczne.py:znajdz_zalegle) -
appka desktopowa nie dziala 24/7, wiec jesli nie byla uruchomiona akurat w
dniu, w ktorym przypomnienie "powinno" pojsc, i tak zostaje pokazane jako
kandydat przy nastepnym uruchomieniu, zamiast zniknac bezpowrotnie.

Kazde przypomnienie idzie NAJWYZEJ RAZ na fakture (UniqueConstraint w
PrzypomnieniePlatnosci) - appka NIGDY nie wysyla niczego automatycznie bez
zgody uzytkownika (patrz znajdz_kandydatow vs wyslij_przypomnienia, ten sam
podzial co faktury cykliczne: "sprawdz i pokaz" vs "wyslij po zatwierdzeniu")."""
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura, Firma, PrzypomnieniePlatnosci
from app.models.enums import TypPrzypomnienia
from app.schemas.przypomnienia import (
    KandydatPrzypomnieniaOut,
    PozycjaDoWyslaniaPrzypomnienia,
    WynikWyslaniaPrzypomnieniaOut,
)
from app.services import email_service, firma as firma_service
from app.services.email_service import BladEmail
from app.services.platnosci import lista_naleznosci

ETYKIETY_TYPU: dict[TypPrzypomnienia, str] = {
    TypPrzypomnienia.PRZED_TERMINEM: "zbliża się termin płatności",
    TypPrzypomnienia.W_DNIU_TERMINU: "dziś mija termin płatności",
    TypPrzypomnienia.PO_TERMINIE: "termin płatności minął",
}

DOMYSLNY_TEMAT = "Przypomnienie o płatności — faktura {numer_faktury}"
DOMYSLNA_TRESC = (
    "Szanowni Państwo,\n\n"
    "uprzejmie przypominamy, że {typ_przypomnienia} za fakturę {numer_faktury} "
    "na kwotę {kwota_pozostala}, z terminem płatności {termin_platnosci}.\n\n"
    "Prosimy o uregulowanie należności.\n\n"
    "Z poważaniem,\n"
    "{nazwa_firmy}"
)


class _SlownikBezpieczny(dict):
    """`str.format_map` z tym slownikiem nigdy nie rzuca KeyError na
    nieznanym placeholderze w recznie edytowanym szablonie (Ustawienia) -
    zamiast tego zostawia go w tekscie tak jak wpisany (`{cos}`), zeby
    uzytkownik od razu widzial literowke zamiast dostac 500 przy wysylce."""

    def __missing__(self, klucz: str) -> str:
        return "{" + klucz + "}"


def _formatuj_kwote(grosze: int, waluta: str) -> str:
    zlote, reszta = divmod(abs(grosze), 100)
    tekst = f"{zlote:,}".replace(",", " ")
    znak = "-" if grosze < 0 else ""
    return f"{znak}{tekst},{reszta:02d} {waluta}"


def _formatuj_date(wartosc: date) -> str:
    return wartosc.strftime("%d.%m.%Y")


def _renderuj(firma: Firma, faktura: Faktura, typ: TypPrzypomnienia) -> tuple[str, str]:
    kontekst = _SlownikBezpieczny(
        numer_faktury=faktura.numer,
        kwota_pozostala=_formatuj_kwote(faktura.kwota_pozostala_grosze, faktura.waluta),
        termin_platnosci=_formatuj_date(faktura.termin_platnosci),
        nazwa_firmy=firma.nazwa,
        nazwa_klienta=faktura.klient.nazwa,
        typ_przypomnienia=ETYKIETY_TYPU[typ],
    )
    temat = (firma.przypomnienia_szablon_temat or DOMYSLNY_TEMAT).format_map(kontekst)
    tresc = (firma.przypomnienia_szablon_tresc or DOMYSLNA_TRESC).format_map(kontekst)
    return temat, tresc


def _juz_wyslane(db: Session, faktura_ids: list[int]) -> dict[int, set[TypPrzypomnienia]]:
    if not faktura_ids:
        return {}
    zapytanie = select(PrzypomnieniePlatnosci.faktura_id, PrzypomnieniePlatnosci.typ).where(
        PrzypomnieniePlatnosci.faktura_id.in_(faktura_ids)
    )
    wynik: dict[int, set[TypPrzypomnienia]] = {}
    for faktura_id, typ in db.execute(zapytanie).all():
        wynik.setdefault(faktura_id, set()).add(typ)
    return wynik


def _progi_dla_faktury(
    firma: Firma, faktura: Faktura, dzisiaj: date
) -> list[TypPrzypomnienia]:
    """Ktore rodzaje przypomnienia SA JUZ NALEZNE (prog przekroczony) dla tej
    faktury, niezaleznie od tego, czy zostaly juz wyslane - filtrowanie "juz
    wyslane" robi wywolujacy (znajdz_kandydatow), zeby ta funkcja pozostala
    czystą kalkulacja kalendarza, latwa do testowania w izolacji."""
    nalezne: list[TypPrzypomnienia] = []

    if firma.przypomnienia_dni_przed is not None:
        prog = faktura.termin_platnosci - timedelta(days=firma.przypomnienia_dni_przed)
        if dzisiaj >= prog:
            nalezne.append(TypPrzypomnienia.PRZED_TERMINEM)

    if firma.przypomnienia_w_dniu_terminu and dzisiaj >= faktura.termin_platnosci:
        nalezne.append(TypPrzypomnienia.W_DNIU_TERMINU)

    if firma.przypomnienia_dni_po is not None:
        prog = faktura.termin_platnosci + timedelta(days=firma.przypomnienia_dni_po)
        if dzisiaj >= prog:
            nalezne.append(TypPrzypomnienia.PO_TERMINIE)

    return nalezne


def znajdz_kandydatow(db: Session, dzisiaj: date | None = None) -> list[KandydatPrzypomnieniaOut]:
    dzisiaj = dzisiaj or date.today()
    firma = firma_service.pobierz_firme(db)

    faktury, _suma = lista_naleznosci(db, dzisiaj)
    faktury = [f for f in faktury if f.kwota_pozostala_grosze > 0]
    wyslane = _juz_wyslane(db, [f.id for f in faktury])

    kandydaci: list[KandydatPrzypomnieniaOut] = []
    for faktura in faktury:
        nalezne = _progi_dla_faktury(firma, faktura, dzisiaj)
        juz_wyslane_dla_faktury = wyslane.get(faktura.id, set())
        for typ in nalezne:
            if typ in juz_wyslane_dla_faktury:
                continue
            kandydaci.append(
                KandydatPrzypomnieniaOut(
                    faktura_id=faktura.id,
                    numer_faktury=faktura.numer,
                    klient_id=faktura.klient_id,
                    klient_nazwa=faktura.klient.nazwa,
                    klient_email=faktura.klient.email,
                    typ=typ,
                    termin_platnosci=faktura.termin_platnosci,
                    kwota_pozostala_grosze=faktura.kwota_pozostala_grosze,
                    waluta=faktura.waluta,
                )
            )
    kandydaci.sort(key=lambda k: (k.termin_platnosci, k.faktura_id))
    return kandydaci


def _pobierz_fakture_z_relacjami(db: Session, faktura_id: int) -> Faktura | None:
    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje), selectinload(Faktura.platnosci), selectinload(Faktura.klient))
        .where(Faktura.id == faktura_id)
    )
    return db.execute(zapytanie).scalar_one_or_none()


def wyslij_przypomnienia(
    db: Session, pozycje: list[PozycjaDoWyslaniaPrzypomnienia]
) -> list[WynikWyslaniaPrzypomnieniaOut]:
    """Wysyla wybrane przypomnienia POJEDYNCZO - blad jednej pozycji (np. brak
    e-maila klienta) nie przerywa reszty paczki, ten sam wzorzec czesciowego
    powodzenia co ksef_service.wyslij_faktury_zbiorczo (Faza 12D)."""
    firma = firma_service.pobierz_firme(db)
    wyniki: list[WynikWyslaniaPrzypomnieniaOut] = []

    for pozycja in pozycje:
        faktura = _pobierz_fakture_z_relacjami(db, pozycja.faktura_id)
        if faktura is None:
            wyniki.append(
                WynikWyslaniaPrzypomnieniaOut(
                    faktura_id=pozycja.faktura_id, typ=pozycja.typ,
                    powodzenie=False, komunikat="Nie znaleziono faktury o podanym id.",
                )
            )
            continue

        if not faktura.klient.email:
            wyniki.append(
                WynikWyslaniaPrzypomnieniaOut(
                    faktura_id=pozycja.faktura_id, typ=pozycja.typ,
                    powodzenie=False,
                    komunikat=f"Klient „{faktura.klient.nazwa}” nie ma zapisanego adresu e-mail.",
                )
            )
            continue

        juz_wyslane = db.execute(
            select(PrzypomnieniePlatnosci.id).where(
                PrzypomnieniePlatnosci.faktura_id == faktura.id,
                PrzypomnieniePlatnosci.typ == pozycja.typ,
            )
        ).scalar_one_or_none()
        if juz_wyslane is not None:
            wyniki.append(
                WynikWyslaniaPrzypomnieniaOut(
                    faktura_id=pozycja.faktura_id, typ=pozycja.typ,
                    powodzenie=False,
                    komunikat="To przypomnienie zostało już wcześniej wysłane dla tej faktury.",
                )
            )
            continue

        temat, tresc = _renderuj(firma, faktura, pozycja.typ)
        try:
            email_service.wyslij_email(faktura.klient.email, temat, tresc)
        except BladEmail as e:
            wyniki.append(
                WynikWyslaniaPrzypomnieniaOut(
                    faktura_id=pozycja.faktura_id, typ=pozycja.typ, powodzenie=False, komunikat=str(e)
                )
            )
            continue

        db.add(
            PrzypomnieniePlatnosci(
                faktura_id=faktura.id, typ=pozycja.typ, adres_email=faktura.klient.email
            )
        )
        db.commit()
        wyniki.append(
            WynikWyslaniaPrzypomnieniaOut(
                faktura_id=pozycja.faktura_id, typ=pozycja.typ, powodzenie=True,
                komunikat=f"Wysłano na adres {faktura.klient.email}.",
            )
        )

    return wyniki


def historia_faktury(db: Session, faktura_id: int) -> list[PrzypomnieniePlatnosci]:
    zapytanie = (
        select(PrzypomnieniePlatnosci)
        .where(PrzypomnieniePlatnosci.faktura_id == faktura_id)
        .order_by(PrzypomnieniePlatnosci.wyslano_o.desc())
    )
    return list(db.execute(zapytanie).scalars().all())
