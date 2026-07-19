"""Wykrywanie obowiazku mechanizmu podzielonej platnosci (MPP / split payment) -
Faza 21. Prog i warunki zweryfikowane wprost w przepisach (art. 105a ust. 1,
art. 106e ust. 1 pkt 18a i zalacznik nr 15 ustawy o VAT), NIE zgadywane:
  - kwota nalezy ogolem (brutto) faktury >= 15 000 zl (prog niezmieniony od
    2019, potwierdzony jako wciaz aktualny)
  - faktura obejmuje co najmniej jedna pozycje z zalacznika nr 15
  - obie strony transakcji (sprzedawca i nabywca) sa podatnikami VAT

Dotyczy WYLACZNIE faktur (nie paragonow) - w tej appce oznacza to kazdy
TypDokumentu przechodzacy przez ten serwis (patrz wywolania w app/services/faktury.py);
proforma i nota korygujaca nigdy nie sa wysylane do KSeF ani traktowane jako
faktura w rozumieniu ustawy o VAT (patrz ksef_fa3_builder.py), ale MOGA nadal
miec ustawiona ta flage informacyjnie/recznie - appka tego nie blokuje.

WAZNE OGRANICZENIA WYNIKAJACE Z ISTNIEJACEGO MODELU DANYCH:
1. PozycjaFaktury nie ma FK do Produkt (wolny tekst, Faza 1/19) - obecnosc
   pozycji z zalacznika 15 jest wiec wykrywana PO NAZWIE (dokladne dopasowanie
   tekstu, bez rozroznienia wielkosci liter) wzgledem aktywnych Produktow
   oznaczonych objety_zalacznikiem_15=True - ten sam, juz zaakceptowany wzorzec
   co dopasowanie WZ z faktury w Fazie 19
   (gui/windows/formularz_wz_z_faktury.py:dopasuj_pozycje_do_produktow).
2. Status VAT nabywcy pochodzi z historii bialej listy (Faza 14,
   WeryfikacjaBialejListy) - appka NIGDY nie odpytuje bialej listy automatycznie
   w tle (offline-first, sprawdzenie tylko na zadanie uzytkownika, przycisk
   "Sprawdz w bialej liscie"). Gdy dla danego klienta nie ma ZADNEGO wpisu w
   historii, funkcja ZAKLADA, ze MPP jest wymagane (potwierdzone z uzytkownikiem
   jako swiadomy wybor) - falszywy pozytyw (dobrowolne zastosowanie MPP) jest
   prawnie nieszkodliwy, falszywy negatyw (brak wymaganej adnotacji na fakturze,
   ktora tego wymagala) niesie realne ryzyko sankcji (dodatkowe zobowiazanie
   podatkowe rzedu 30% kwoty VAT z pozycji objetych zalacznikiem 15).

To tylko SUGESTIA poczatkowa - Faktura.wymaga_mpp mozna zawsze recznie nadpisac
(patrz app/services/faktury.py), bo dobrowolne zastosowanie MPP jest dozwolone
nawet ponizej progu / dla towarow spoza zalacznika 15.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Klient, Produkt, WeryfikacjaBialejListy

# 15 000 zl brutto (art. 105a ust. 1 ustawy o VAT) - w groszach.
PROG_MPP_GROSZE = 1_500_000

# Wartosci pola statusVat zwracane przez wykaz podatnikow VAT (wl-api.mf.gov.pl,
# Faza 14) - jesli ostatnie znane sprawdzenie bialej listy dla klienta wskazuje
# jedna z nich, nabywca NIE jest czynnym podatnikiem VAT, wiec MPP nie dotyczy
# tej transakcji niezaleznie od kwoty/zalacznika 15.
STATUSY_VAT_WYKLUCZAJACE_MPP = frozenset({"Zwolniony", "Niezarejestrowany"})


def zawiera_pozycje_zalacznika_15(
    db: Session, firma_id: int, nazwy_pozycji: list[str]
) -> bool:
    """Dopasowanie po nazwie (bez rozroznienia wielkosci liter) wzgledem
    aktywnych produktow firmy oznaczonych jako objete zalacznikiem nr 15."""
    if not nazwy_pozycji:
        return False
    nazwy_znormalizowane = {n.strip().lower() for n in nazwy_pozycji}
    zapytanie = select(Produkt.nazwa).where(
        Produkt.firma_id == firma_id,
        Produkt.objety_zalacznikiem_15.is_(True),
        Produkt.aktywny.is_(True),
    )
    nazwy_produktow_zal15 = {
        n.strip().lower() for n in db.execute(zapytanie).scalars().all()
    }
    return bool(nazwy_znormalizowane & nazwy_produktow_zal15)


def _ostatni_status_vat_nabywcy(db: Session, klient_id: int) -> str | None:
    zapytanie = (
        select(WeryfikacjaBialejListy.status_vat)
        .where(WeryfikacjaBialejListy.klient_id == klient_id)
        .order_by(WeryfikacjaBialejListy.sprawdzono_o.desc())
        .limit(1)
    )
    return db.execute(zapytanie).scalar_one_or_none()


def sugeruj_wymaga_mpp(
    db: Session,
    klient: Klient,
    suma_brutto_grosze: int,
    nazwy_pozycji: list[str],
) -> bool:
    """Automatyczna sugestia obowiazku MPP dla nowej/edytowanej faktury -
    zrodlo prawdy wywolywane z app/services/faktury.py, gdy klient/appka nie
    nadpisze wartosci recznie."""
    if suma_brutto_grosze < PROG_MPP_GROSZE:
        return False
    if not (klient.nip and klient.nip.strip()):
        # Brak NIP = kontrahent konsumencki (B2C) - MPP nigdy nie dotyczy
        # sprzedazy na rzecz podmiotu, ktory nie jest (znanym appce) podatnikiem VAT.
        return False
    if not zawiera_pozycje_zalacznika_15(db, klient.firma_id, nazwy_pozycji):
        return False

    status_vat = _ostatni_status_vat_nabywcy(db, klient.id)
    if status_vat in STATUSY_VAT_WYKLUCZAJACE_MPP:
        return False
    # Status "Czynny" LUB nigdy niesprawdzony (None) -> zaloz obowiazek MPP.
    return True
