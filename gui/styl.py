# Centralny plik motywu (Faza 16A). Kazda wartosc wizualna uzywana w gui/ ma
# zrodlo TUTAJ - kolory, odstepy, promienie zaokraglen, typografia - zeby
# zmiana wygladu appki nigdy nie wymagala grzebania po wielu plikach widokow.
#
# Kolory sa krotkami (jasny, ciemny) zgodnie z konwencja customtkinter: kazdy
# widget CTk (fg_color/text_color/border_color/hover_color/button_color/...)
# przyjmuje taka krotke i sam wybiera wlasciwy odcien wedlug aktualnego trybu
# wygladu (ctk.set_appearance_mode, patrz gui/nastawienia.py). Dzieki temu
# WSZYSTKIE dotychczasowe widoki dostaly obsluge trybu ciemnego bez zadnych
# zmian w kodzie - odwoluja sie wylacznie do stalych z tego modulu.

KOLOR_TLO = ("#F4F6FB", "#12141F")
KOLOR_SIDEBAR = ("#1B2340", "#141833")
KOLOR_SIDEBAR_TEKST = ("#E8EAF3", "#E8EAF3")
KOLOR_AKCENT = ("#3D5AFE", "#5B72FF")
KOLOR_AKCENT_HOVER = ("#5470FF", "#7186FF")
KOLOR_KARTA = ("#FFFFFF", "#1B1F30")
KOLOR_OBRAMOWANIE = ("#E1E4EC", "#2B3149")
KOLOR_TEKST_GLOWNY = ("#1C2333", "#EEF0F7")
KOLOR_TEKST_DRUGORZEDNY = ("#6B7280", "#9AA0B4")
KOLOR_WIERSZ_PARZYSTY = ("#FFFFFF", "#1B1F30")
KOLOR_WIERSZ_NIEPARZYSTY = ("#F7F8FC", "#20253A")
KOLOR_WIERSZ_ZAZNACZONY = ("#E8ECFF", "#2C3563")
KOLOR_NAGLOWEK_TABELI = ("#EEF0F7", "#242A42")
KOLOR_BLAD = ("#DC2626", "#F87171")
KOLOR_SUKCES = ("#16A34A", "#4ADE80")
KOLOR_OSTRZEZENIE = ("#D97706", "#FBBF24")
KOLOR_OSTRZEZENIE_TLO = ("#FEF3C7", "#453A17")
KOLOR_BLAD_TLO = ("#FEE2E2", "#3F1D1D")
KOLOR_SUKCES_TLO = ("#DCFCE7", "#123822")

# Ikony (gui/ikony.py) sa rastrowe (PIL), wiec potrzebuja pojedynczego,
# rozwiazanego koloru RGB - nie moga uzyc krotki (jasny, ciemny) jak widgety
# CTk. Te trzy stale sa jedynym miejscem, z ktorego ikony biora kolor, zeby
# zostaly spojne z paleta powyzej.
KOLOR_IKONY_NA_STALE_CIEMNYM = "#EDEFF7"  # pasek boczny, przyciski akcentowe - tlo nie zmienia sie z trybem
KOLOR_IKONY_JASNY_TRYB = "#1C2333"  # przyciski drugorzedne (obrys) w trybie jasnym
KOLOR_IKONY_CIEMNY_TRYB = "#EEF0F7"  # przyciski drugorzedne (obrys) w trybie ciemnym

# Kolor tekstu statusu (status_efektywny) w tabelach/szczegolach faktury.
KOLORY_STATUSU: dict[str, tuple[str, str]] = {
    "robocza": KOLOR_TEKST_DRUGORZEDNY,
    "wystawiona": KOLOR_TEKST_GLOWNY,
    "wyslana": KOLOR_TEKST_GLOWNY,
    "oplacona_czesciowo": KOLOR_OSTRZEZENIE,
    "oplacona": KOLOR_SUKCES,
    "po_terminie": KOLOR_BLAD,
    "anulowana": KOLOR_TEKST_DRUGORZEDNY,
}

# Kolor tekstu statusu oferty (Faza 24) - mirror KOLORY_STATUSU. "wygasla" uzywa
# tej samej "pilnosci" co "po_terminie" dla faktur (termin minal, wymaga uwagi).
KOLORY_STATUSU_OFERTY: dict[str, tuple[str, str]] = {
    "robocza": KOLOR_TEKST_DRUGORZEDNY,
    "wyslana": KOLOR_TEKST_GLOWNY,
    "zaakceptowana": KOLOR_SUKCES,
    "odrzucona": KOLOR_BLAD,
    "wygasla": KOLOR_BLAD,
}

SZEROKOSC_SIDEBAR = 220
ODSTEP_MIKRO = 4
ODSTEP_ETYKIETA = 2
ODSTEP_RAMKA_TABELI = 1
ODSTEP_MALY = 8
ODSTEP_SREDNI = 16
ODSTEP_DUZY = 24
PROMIEN_NAROZNIKA = 8

# Krotki (nazwa, rozmiar, waga), NIE ctk.CTkFont(...) - CTkFont wymaga juz istniejacego
# roota Tk, a ten modul jest importowany zanim ctk.CTk() powstanie.
NAGLOWEK_1 = ("Segoe UI", 22, "bold")
NAGLOWEK_2 = ("Segoe UI", 16, "bold")
NAGLOWEK_KAFELEK = ("Segoe UI", 26, "bold")
CZCIONKA_ETYKIETA = ("Segoe UI", 13)
CZCIONKA_TRESC = ("Segoe UI", 13)
CZCIONKA_TRESC_POGRUBIONA = ("Segoe UI", 13, "bold")
CZCIONKA_DROBNA = ("Segoe UI", 11)
