from typing import Callable

import customtkinter as ctk

from gui import styl
from gui.windows.baza_formularza import OknoDialogu

_KOLORY_ALERTU = {
    "info": (styl.KOLOR_TEKST_GLOWNY, styl.KOLOR_KARTA),
    "sukces": (styl.KOLOR_SUKCES, styl.KOLOR_SUKCES_TLO),
    "blad": (styl.KOLOR_BLAD, styl.KOLOR_BLAD_TLO),
    "ostrzezenie": (styl.KOLOR_OSTRZEZENIE, styl.KOLOR_OSTRZEZENIE_TLO),
}


class DialogAlertu(OknoDialogu):
    """Wlasny, stylizowany odpowiednik messagebox.show{info,error,warning}
    (Faza 16C, rozszerzone przy audycie spojnosci wizualnej) - jedyny OK,
    kolorowany wg `typ` tokenami z 16A zamiast natywnej ramki Windows/Tk."""

    def __init__(self, master, tytul: str, tekst: str, typ: str = "info"):
        super().__init__(master)
        self.title(tytul)
        self.resizable(False, False)

        kolor_tekstu, kolor_tla = _KOLORY_ALERTU.get(typ, _KOLORY_ALERTU["info"])

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)

        pasek_tytulu = ctk.CTkFrame(
            kontener, fg_color=kolor_tla, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        pasek_tytulu.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))
        ctk.CTkLabel(
            pasek_tytulu, text=tytul, font=styl.CZCIONKA_TRESC_POGRUBIONA,
            text_color=kolor_tekstu, anchor="w", wraplength=400, justify="left",
        ).pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY)

        ctk.CTkLabel(
            kontener, text=tekst, font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_GLOWNY, wraplength=400,
            justify="left", anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        przycisk = ctk.CTkButton(
            kontener, text="OK", fg_color=styl.KOLOR_AKCENT,
            hover_color=styl.KOLOR_AKCENT_HOVER, command=self.destroy,
        )
        przycisk.pack(fill="x")
        self.bind("<Return>", lambda _z: self.destroy())
        przycisk.focus_set()


def pokaz_alert(rodzic, tekst: str, tytul: str = "Informacja", typ: str = "info") -> None:
    """Wlasny, blokujacy odpowiednik messagebox.show{info,error,warning}.
    Celowo NADAL blokujacy (jak natywny messagebox), w odroznieniu od
    `pokaz_toast` - kilka wywolan tuz PRZED zamknieciem calej aplikacji
    (np. po przywroceniu kopii zapasowej) potrzebuje potwierdzenia, ktore
    uzytkownik na pewno zobaczy, zanim proces sie zakonczy; nieblokujacy
    toast znikalby razem z procesem niezauwazony."""
    dialog = DialogAlertu(rodzic, tytul, tekst, typ)
    dialog.wait_window()


def komunikat_bledu(rodzic, tekst: str, tytul: str = "Błąd") -> None:
    pokaz_alert(rodzic, tekst, tytul, typ="blad")


def komunikat_info(rodzic, tekst: str, tytul: str = "Informacja") -> None:
    pokaz_alert(rodzic, tekst, tytul, typ="info")


def komunikat_ostrzezenie(rodzic, tekst: str, tytul: str = "Ostrzeżenie") -> None:
    pokaz_alert(rodzic, tekst, tytul, typ="ostrzezenie")


class DialogPotwierdzenia(OknoDialogu):
    """Wlasny, stylizowany odpowiednik messagebox.askyesno (Faza 16C,
    rozszerzone przy audycie spojnosci wizualnej) - dla potwierdzen
    destrukcyjnych/znaczacych akcji. `niebezpieczne=True` koloruje przycisk
    potwierdzenia na czerwono (KOLOR_BLAD) I przenosi domyslny fokus/Enter
    na przycisk odmowy - przypadkowe Enter/spacja nie powinno moc samo z
    siebie potwierdzic nieodwracalnej akcji."""

    def __init__(
        self,
        master,
        tytul: str,
        tekst: str,
        tekst_tak: str = "Tak",
        tekst_nie: str = "Nie",
        niebezpieczne: bool = False,
    ):
        super().__init__(master)
        self.title(tytul)
        self.resizable(False, False)
        self.wynik = False

        kontener = ctk.CTkFrame(self, fg_color="transparent")
        kontener.pack(fill="both", expand=True, padx=styl.ODSTEP_DUZY, pady=styl.ODSTEP_DUZY)

        if niebezpieczne:
            pasek_ostrzezenia = ctk.CTkFrame(
                kontener, fg_color=styl.KOLOR_BLAD_TLO, corner_radius=styl.PROMIEN_NAROZNIKA
            )
            pasek_ostrzezenia.pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))
            ctk.CTkLabel(
                pasek_ostrzezenia, text=tytul, font=styl.CZCIONKA_TRESC_POGRUBIONA,
                text_color=styl.KOLOR_BLAD, anchor="w", wraplength=400, justify="left",
            ).pack(fill="x", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY)

        ctk.CTkLabel(
            kontener, text=tekst, font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_TEKST_GLOWNY, wraplength=400,
            justify="left", anchor="w",
        ).pack(fill="x", pady=(0, styl.ODSTEP_SREDNI))

        pasek = ctk.CTkFrame(kontener, fg_color="transparent")
        pasek.pack(fill="x")
        pasek.grid_columnconfigure((0, 1), weight=1)

        przycisk_nie = ctk.CTkButton(
            pasek, text=tekst_nie, fg_color="transparent", border_width=1,
            border_color=styl.KOLOR_OBRAMOWANIE, text_color=styl.KOLOR_TEKST_GLOWNY,
            hover_color=styl.KOLOR_WIERSZ_NIEPARZYSTY, command=self._na_nie,
        )
        przycisk_nie.grid(row=0, column=0, sticky="ew", padx=(0, styl.ODSTEP_MALY))

        kolor_tak = styl.KOLOR_BLAD if niebezpieczne else styl.KOLOR_AKCENT
        hover_tak = styl.KOLOR_BLAD if niebezpieczne else styl.KOLOR_AKCENT_HOVER
        przycisk_tak = ctk.CTkButton(
            pasek, text=tekst_tak, fg_color=kolor_tak, hover_color=hover_tak,
            command=self._na_tak,
        )
        przycisk_tak.grid(row=0, column=1, sticky="ew")

        domyslny = self._na_nie if niebezpieczne else self._na_tak
        self.bind("<Return>", lambda _z: domyslny())
        (przycisk_nie if niebezpieczne else przycisk_tak).focus_set()

    def _na_tak(self) -> None:
        self.wynik = True
        self.destroy()

    def _na_nie(self) -> None:
        self.wynik = False
        self.destroy()


def potwierdz(
    rodzic,
    tekst: str,
    tytul: str = "Potwierdź",
    tekst_tak: str = "Tak",
    tekst_nie: str = "Nie",
    niebezpieczne: bool = False,
) -> bool:
    """Wlasny, stylizowany odpowiednik messagebox.askyesno - patrz
    DialogPotwierdzenia. Blokuje (wait_window) i zwraca decyzje uzytkownika
    dokladnie jak natywny askyesno, wiec istniejace wywolania `if not
    messagebox.askyesno(...)` zamieniaja sie na `if not potwierdz(...)` bez
    zmiany reszty logiki wywolujacej."""
    dialog = DialogPotwierdzenia(rodzic, tytul, tekst, tekst_tak, tekst_nie, niebezpieczne)
    dialog.wait_window()
    return dialog.wynik


def ustaw_tekst_ladowania(
    przycisk: ctk.CTkButton,
    w_trakcie: bool,
    tekst_zwykly: str,
    tekst_ladowania: str = "Zapisywanie...",
) -> None:
    """Wskaznik ladowania dla akcji sieciowych spod przycisku (zapis, PDF,
    generowanie dokumentu) - zamiast samego wyszarzenia przycisku, tekst tez
    mowi co sie dzieje (Faza 16C, punkt 1)."""
    przycisk.configure(
        state="disabled" if w_trakcie else "normal",
        text=tekst_ladowania if w_trakcie else tekst_zwykly,
    )


class Banner(ctk.CTkFrame):
    """Nieblokujacy banner bledu walidacji, osadzony w formularzu (Faza 16C,
    punkt 2) - w odroznieniu od messagebox.showerror nie przerywa pracy
    modalnym oknem. Domyslnie ukryty; wolajacy rejestruje docelowa geometrie
    (pack lub grid) przez `ustaw_geometrie`, bo Banner nie wie, ktorego
    menedzera geometrii uzywa konkretny formularz."""

    def __init__(self, master):
        super().__init__(
            master, fg_color=styl.KOLOR_BLAD_TLO, corner_radius=styl.PROMIEN_NAROZNIKA
        )
        self._etykieta = ctk.CTkLabel(
            self,
            text="",
            font=styl.CZCIONKA_TRESC,
            text_color=styl.KOLOR_BLAD,
            anchor="w",
            justify="left",
            wraplength=560,
        )
        self._etykieta.pack(
            fill="x", padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY
        )
        self._umiesc = lambda: None

    def ustaw_geometrie(self, umiesc) -> None:
        """`umiesc` to funkcja bezargumentowa wywolujaca .pack(...) albo
        .grid(...) z parametrami wlasciwymi dla danego formularza."""
        self._umiesc = umiesc

    def pokaz(self, tekst: str) -> None:
        self._etykieta.configure(text=tekst)
        self._umiesc()

    def ukryj(self) -> None:
        self.pack_forget()
        self.grid_forget()


def podepnij_maske_kodu_pocztowego(pole: ctk.CTkEntry) -> None:
    """Maska formatu XX-XXX (kod pocztowy) w trakcie pisania - uzytkownik
    wpisuje same cyfry, myslnik po dwoch cyfrach dokleja sie sam, zamiast
    tylko akceptowac myslnik jesli uzytkownik wpisze go recznie. Przy okazji
    odrzuca kazdy znak, ktory nie jest cyfra (backend i tak wymaga formatu
    XX-XXX - patrz app/schemas/firma.py i app/schemas/klient.py
    waliduj_kod_pocztowy - to tylko przenosi te sama regule na wczesniej,
    zanim uzytkownik dostanie blad walidacji)."""

    def sformatuj(_zdarzenie=None) -> None:
        cyfry = "".join(znak for znak in pole.get() if znak.isdigit())[:5]
        sformatowany = f"{cyfry[:2]}-{cyfry[2:]}" if len(cyfry) > 2 else cyfry
        if sformatowany != pole.get():
            pole.delete(0, "end")
            pole.insert(0, sformatowany)

    pole.bind("<KeyRelease>", sformatuj)


def podepnij_limit_cyfr(pole: ctk.CTkEntry, maks_cyfr: int) -> None:
    """Blokuje wpisanie WIECEJ niz maks_cyfr cyfr do pola (np. NIP - polski
    format ma dokladnie 10 cyfr) zamiast pozwalac wpisac za duzo i dopiero
    walidowac po fakcie. Celowo obcina tylko NADMIAROWE znaki PO
    maks_cyfr-tej cyfrze, nie usuwa myslnikow/spacji wpisanych WCZESNIEJ -
    Faza 27b naprawila akceptowanie NIP-u sformatowanego myslnikami/spacjami
    (patrz app/schemas/klient.py waliduj_nip), wiec ta maska nie powinna
    tego cofac przez wymuszanie samych cyfr."""

    def sformatuj(_zdarzenie=None) -> None:
        tekst = pole.get()
        cyfry_widziane = 0
        for indeks, znak in enumerate(tekst):
            if znak.isdigit():
                cyfry_widziane += 1
                if cyfry_widziane > maks_cyfr:
                    obciety = tekst[:indeks]
                    pole.delete(0, "end")
                    pole.insert(0, obciety)
                    return

    pole.bind("<KeyRelease>", sformatuj)


def przewin_na_gore(ramka: ctk.CTkScrollableFrame) -> None:
    """Resetuje pozycje przewiniecia CTkScrollableFrame do samej gory.

    customtkinter NIE robi tego samo przy zmianie wysokosci zawartosci -
    zweryfikowane wprost (reprodukcja w izolowanym skrypcie): po
    pack_forget() dluzszej zawartosci i spakowaniu krotszej w tym samym
    CTkScrollableFrame, scrollregion i pozycja przewiniecia (yview) NIE
    kurcza sie razem z nowa, krotsza zawartoscia - jesli byla przewinieta w
    dol, nowa (krotsza) zawartosc renderuje sie poprawnie, ale CALKOWICIE
    poza widocznym obszarem (wyglada jak brakujace pole). Wlasciwe przy
    przelaczaniu calych "krokow"/ekranow (np. kolejne kroki kreatora
    pierwszego uruchomienia) - kazdy nowy krok powinien i tak zaczynac sie
    od gory."""
    ramka._parent_canvas.yview_moveto(0.0)


def odswiez_obszar_przewijania(ramka: ctk.CTkScrollableFrame) -> None:
    """Wymusza natychmiastowe przeliczenie scrollregion CTkScrollableFrame po
    programowej zmianie ukladu (pack/pack_forget) WEWNATRZ jego zawartosci,
    bez zmiany biezacej pozycji przewiniecia (w odroznieniu od przewin_na_gore
    powyzej - tu przewijanie uzytkownika ma zostac tam, gdzie bylo).

    Bez tego canvas polega wylacznie na zdarzeniu <Configure>, ktore przy
    aktywnym, szybkim przewijaniu uzytkownika moze zdazyc sie PRZED albo w
    trakcie zmiany geometrii wywolanej asynchronicznie (np. dane firmy
    wczytane w tle po otwarciu Ustawien) - powoduje to widoczne bledy
    renderowania (przesuniete/nachodzace karty), ten sam mechanizm co
    przewin_na_gore, tylko wyzwalany asynchronicznie zamiast przy jawnej
    zmianie ekranu.

    UWAGA - NIE uzywac dla duzych, w pelni wymienianych tabel (setki
    wierszy, np. gui/windows/tabela.py:Tabela.ustaw_dane) - zmierzone przy
    diagnozie wolnego ladowania listy Klientow: update_idletasks() na
    CTkScrollableFrame z ~200 swiezo dograsowanymi wierszami kaskaduje przez
    wlasny, zagniezdzony update_idletasks() w customtkinter
    (CTkScrollbar._draw()), co potrafilo zablokowac GUI na kilkanascie
    sekund. Tabela CELOWO tego nie wola - patrz komentarz w ustaw_dane."""
    ramka.update_idletasks()
    ramka._parent_canvas.configure(scrollregion=ramka._parent_canvas.bbox("all"))


def debounce_wyszukiwania(
    widget: ctk.CTkBaseClass, wywolaj: Callable[[], None], opoznienie_ms: int = 250
) -> Callable[[object], None]:
    """Zwraca handler do podpiecia pod <KeyRelease> pola wyszukiwania w
    listach (Tabela) - odklada faktyczne przebudowanie tabeli o
    opoznienie_ms od OSTATNIEGO nacisniecia klawisza, zamiast przebudowywac
    setki widgetow wierszy na KAZDA wpisana literke. Kolejne nacisniecie
    przed uplywem opoznienia anuluje poprzednio zaplanowane wywolanie."""
    stan_id: dict[str, str | None] = {"after_id": None}

    def handler(_zdarzenie=None) -> None:
        if stan_id["after_id"] is not None:
            widget.after_cancel(stan_id["after_id"])
        stan_id["after_id"] = widget.after(opoznienie_ms, wywolaj)

    return handler


def formatuj_srodowisko_ksef(srodowisko: str) -> tuple[str, tuple, tuple]:
    """Tekst + (kolor_tekstu, kolor_tla) spojne w CALEJ appce dla oznaczenia
    aktywnego srodowiska KSeF (Faza 12D) - PRODUKCYJNE zawsze rzuca sie w
    oczy (czerwone tlo), zeby nigdy nie bylo watpliwosci, do ktorego systemu
    appka sie laczy. Jedno zrodlo tekstu/kolorow dla Ustawien i kazdego
    miejsca, z ktorego mozna cos wyslac/pobrac z KSeF (szczegoly faktury,
    lista faktur, dokumenty kosztowe)."""
    if srodowisko == "produkcyjne":
        return "●  ŚRODOWISKO PRODUKCYJNE — prawdziwy system KSeF", styl.KOLOR_BLAD, styl.KOLOR_BLAD_TLO
    return "●  ŚRODOWISKO TESTOWE (sandbox Ministerstwa Finansów)", styl.KOLOR_SUKCES, styl.KOLOR_SUKCES_TLO


def etykieta_srodowiska_ksef(master, srodowisko: str, pogrubiona: bool = False) -> ctk.CTkLabel:
    """Kompaktowa etykieta do umieszczenia obok kazdego przycisku wysylajacego/
    pobierajacego cos z KSeF - patrz formatuj_srodowisko_ksef."""
    tekst, kolor_tekstu, kolor_tla = formatuj_srodowisko_ksef(srodowisko)
    return ctk.CTkLabel(
        master,
        text=tekst,
        font=styl.CZCIONKA_TRESC_POGRUBIONA if pogrubiona else styl.CZCIONKA_DROBNA,
        text_color=kolor_tekstu,
        fg_color=kolor_tla,
        corner_radius=styl.PROMIEN_NAROZNIKA,
        anchor="w",
    )


_CZAS_TOASTU_MS = 3500

_KOLORY_TOASTU = {
    "sukces": (styl.KOLOR_SUKCES_TLO, styl.KOLOR_SUKCES),
    "blad": (styl.KOLOR_BLAD_TLO, styl.KOLOR_BLAD),
    "ostrzezenie": (styl.KOLOR_OSTRZEZENIE_TLO, styl.KOLOR_OSTRZEZENIE),
}


def pokaz_toast(widget, tekst: str, typ: str = "sukces") -> None:
    """Nieblokujacy komunikat sukcesu (Faza 16C, punkt 2) - znika sam po
    kilku sekundach, w przeciwienstwie do messagebox.showinfo. Zaczepiony o
    okno najwyzszego poziomu (`winfo_toplevel`) danego widgetu, zeby dzialal
    zarowno z widoku w glownym oknie, jak i z formularza w osobnym Toplevelu.
    Kolejny toast na tym samym oknie zastepuje poprzedni, zamiast sie stakowac."""
    root = widget.winfo_toplevel()
    poprzedni = getattr(root, "_aktywny_toast", None)
    if poprzedni is not None and poprzedni.winfo_exists():
        poprzedni.destroy()

    kolor_tla, kolor_tekstu = _KOLORY_TOASTU.get(typ, _KOLORY_TOASTU["sukces"])

    toast = ctk.CTkFrame(
        root, fg_color=kolor_tla, corner_radius=styl.PROMIEN_NAROZNIKA
    )
    ctk.CTkLabel(
        toast,
        text=tekst,
        font=styl.CZCIONKA_TRESC,
        text_color=kolor_tekstu,
        wraplength=420,
        justify="left",
    ).pack(padx=styl.ODSTEP_SREDNI, pady=styl.ODSTEP_MALY)
    toast.place(relx=1.0, rely=1.0, x=-styl.ODSTEP_DUZY, y=-styl.ODSTEP_DUZY, anchor="se")

    root._aktywny_toast = toast

    def _zamknij() -> None:
        if toast.winfo_exists():
            toast.destroy()
        if getattr(root, "_aktywny_toast", None) is toast:
            root._aktywny_toast = None

    toast.after(_CZAS_TOASTU_MS, _zamknij)
