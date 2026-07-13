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


class TypDokumentuMagazynowego(str, enum.Enum):
    PZ = "pz"  # Przyjecie Zewnetrzne
    WZ = "wz"  # Wydanie Zewnetrzne
    PW = "pw"  # Przyjecie Wewnetrzne
    RW = "rw"  # Rozchod Wewnetrzny
    MM = "mm"  # Przesuniecie Miedzymagazynowe


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
