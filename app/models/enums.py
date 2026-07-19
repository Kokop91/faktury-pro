import enum


class StawkaVat(str, enum.Enum):
    STAWKA_23 = "23"
    STAWKA_8 = "8"
    STAWKA_5 = "5"
    STAWKA_0 = "0"
    ZW = "zw"


class TypDokumentu(str, enum.Enum):
    FAKTURA_VAT = "faktura_vat"
    PROFORMA = "proforma"
    FAKTURA_ZALICZKOWA = "faktura_zaliczkowa"
    FAKTURA_KONCOWA = "faktura_koncowa"
    FAKTURA_KORYGUJACA = "faktura_korygujaca"
    NOTA_KORYGUJACA = "nota_korygujaca"
    RACHUNEK = "rachunek"


class StatusFaktury(str, enum.Enum):
    ROBOCZA = "robocza"
    WYSTAWIONA = "wystawiona"
    WYSLANA = "wyslana"
    OPLACONA_CZESCIOWO = "oplacona_czesciowo"
    OPLACONA = "oplacona"
    PO_TERMINIE = "po_terminie"
    ANULOWANA = "anulowana"


class StatusOferty(str, enum.Enum):
    """Status oferty (Faza 24) - niezalezny od StatusFaktury, oferta NIE jest
    dokumentem ksiegowym i nie podlega KSeF/JPK. WYGASLA jest wylacznie
    wartoscia status_efektywny (patrz app/services/oferty.py:
    oblicz_status_efektywny) - nigdy nie pojawia sie jako klucz ani wartosc w
    DOZWOLONE_PRZEJSCIA_STATUSU, wiec nie da sie jej trwale zapisac."""

    ROBOCZA = "robocza"
    WYSLANA = "wyslana"
    ZAAKCEPTOWANA = "zaakceptowana"
    ODRZUCONA = "odrzucona"
    WYGASLA = "wygasla"


class StatusDokumentuKosztowego(str, enum.Enum):
    """Stan przegladu dokumentu kosztowego (Faza 12C) pobranego z KSeF - CZYSTO
    rejestrowy/informacyjny, bez integracji ksiegowej (to potencjalny temat
    na przyszlosc, poza zakresem tej fazy)."""

    NOWA = "nowa"
    ZAAKCEPTOWANA = "zaakceptowana"
    DO_WYJASNIENIA = "do_wyjasnienia"


class StatusKsef(str, enum.Enum):
    """Stan wysylki faktury do KSeF (Faza 12B) - niezalezny od StatusFaktury
    (ta sama faktura moze byc np. 'wystawiona' i 'ksef_przyjeta' jednoczesnie)."""

    NIE_WYSLANA = "nie_wyslana"
    WYSYLANIE_W_TOKU = "wysylanie_w_toku"
    PRZYJETA = "przyjeta"
    ODRZUCONA = "odrzucona"


# Typy dokumentu, ktore FA(3) potrafi wyrazic (posiadaja odpowiadajaca wartosc
# pola RodzajFaktury) - PROFORMA i NOTA_KORYGUJACA nie sa "faktura" w rozumieniu
# ustawy o VAT i nie maja zadnej reprezentacji w schemacie FA(3) (zweryfikowane
# wprost w schemat_FA3_v1-0E.xsd, typ TRodzajFaktury - brak wartosci dla nich),
# wiec nie moga byc wyslane do KSeF w ogole, niezaleznie od tresci.
TYPY_DOKUMENTU_WYSYLANE_DO_KSEF: frozenset[TypDokumentu] = frozenset(
    {
        TypDokumentu.FAKTURA_VAT,
        TypDokumentu.FAKTURA_ZALICZKOWA,
        TypDokumentu.FAKTURA_KONCOWA,
        TypDokumentu.FAKTURA_KORYGUJACA,
        TypDokumentu.RACHUNEK,
    }
)


class TypDokumentuMagazynowego(str, enum.Enum):
    PZ = "pz"  # Przyjecie Zewnetrzne
    WZ = "wz"  # Wydanie Zewnetrzne
    PW = "pw"  # Przyjecie Wewnetrzne
    RW = "rw"  # Rozchod Wewnetrzny
    MM = "mm"  # Przesuniecie Miedzymagazynowe


class TrybBlokadyStanu(str, enum.Enum):
    BLOKUJ = "blokuj"
    OSTRZEGAJ = "ostrzegaj"


class StatusInwentaryzacji(str, enum.Enum):
    W_TRAKCIE = "w_trakcie"
    ZAKONCZONA = "zakonczona"


class CzestotliwoscCykliczna(str, enum.Enum):
    MIESIECZNA = "miesieczna"
    KWARTALNA = "kwartalna"
    ROCZNA = "roczna"


class StatusSzablonuCyklicznego(str, enum.Enum):
    AKTYWNY = "aktywny"
    WSTRZYMANY = "wstrzymany"


class TypPrzypomnienia(str, enum.Enum):
    """Trzy niezalezne rodzaje przypomnien o platnosci (Faza 23) - kazdy
    wysylany co najwyzej RAZ na fakture (patrz unique constraint na
    PrzypomnieniePlatnosci w app/models/przypomnienie_platnosci.py), niezaleznie
    od tego, ile razy zmieni sie liczba dni w harmonogramie w Ustawieniach."""

    PRZED_TERMINEM = "przed_terminem"
    W_DNIU_TERMINU = "w_dniu_terminu"
    PO_TERMINIE = "po_terminie"


class TypPodatnika(str, enum.Enum):
    """Forma prawna firmy (Faza 13 - wplywa na ksztalt sekcji Podmiot1 w
    JPK_V7: osoba fizyczna wymaga imienia/nazwiska/daty urodzenia, osoba
    niefizyczna - pelnej nazwy). Konfigurowalne, bo appka ma obslugiwac
    zarowno JDG jak i spolki."""

    OSOBA_FIZYCZNA = "osoba_fizyczna"
    OSOBA_NIEFIZYCZNA = "osoba_niefizyczna"


# Typy dokumentu dozwolone jako szablon cykliczny (Faza 15) - wylacznie
# dokumenty "samodzielne", ktore nie odnosza sie do innego konkretnego
# dokumentu (korekty/nota/koncowa z definicji nie moga byc cykliczne, bo
# kazda z nich koryguje/rozlicza JEDEN konkretny wczesniejszy dokument).
DOZWOLONE_TYPY_SZABLONU_CYKLICZNEGO: frozenset[TypDokumentu] = frozenset(
    {
        TypDokumentu.FAKTURA_VAT,
        TypDokumentu.PROFORMA,
        TypDokumentu.FAKTURA_ZALICZKOWA,
        TypDokumentu.RACHUNEK,
    }
)


# Klasyfikacja typow dokumentu wg wymagan co do dokument_powiazany_id/przyczyna_korekty.
# Wspoldzielone przez schematy (szybka walidacja 422) i serwis (zrodlo prawdy, patrz
# app/services/faktury.py) - stad zyja tutaj, a nie w jednej z tych warstw.
TYPY_WYMAGAJACE_DOKUMENTU_POWIAZANEGO: frozenset[TypDokumentu] = frozenset(
    {
        TypDokumentu.FAKTURA_KORYGUJACA,
        TypDokumentu.NOTA_KORYGUJACA,
        TypDokumentu.FAKTURA_KONCOWA,
    }
)
TYPY_WYMAGAJACE_PRZYCZYNY_KOREKTY: frozenset[TypDokumentu] = frozenset(
    {TypDokumentu.FAKTURA_KORYGUJACA, TypDokumentu.NOTA_KORYGUJACA}
)
DOZWOLONE_TYPY_DOKUMENTU_KORYGOWANEGO: frozenset[TypDokumentu] = frozenset(
    {
        TypDokumentu.FAKTURA_VAT,
        TypDokumentu.FAKTURA_ZALICZKOWA,
        TypDokumentu.FAKTURA_KONCOWA,
        TypDokumentu.RACHUNEK,
    }
)
