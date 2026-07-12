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
