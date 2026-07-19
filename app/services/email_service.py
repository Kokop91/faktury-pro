"""Generyczna wysylka e-mail przez SMTP (Faza 23, Etap 4) - fundament, na
ktorym Faza 23 buduje przypomnienia o platnosciach
(app/services/przypomnienia_service.py). Uzywa wylacznie standardowej
biblioteki (smtplib/email) - bez dodatkowych zaleznosci.

Swiadomie NIE obsluguje jeszcze wysylki samej faktury mailem (ten temat z
pierwotnego PLAN_PROJEKTU.md pozostaje osobnym, przyszlym zadaniem) - `wyslij_email`
przyjmuje jednak opcjonalne zalaczniki, zeby nie trzeba bylo przepisywac tej
funkcji, gdy ten temat wroci."""
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

from app.services import email_ustawienia

TIMEOUT_S = 15.0


@dataclass
class Zalacznik:
    nazwa_pliku: str
    tresc: bytes
    typ_mime: str = "application/octet-stream"


class BladEmail(Exception):
    pass


def _polacz(dane: dict) -> smtplib.SMTP:
    if dane["szyfrowanie"] == "ssl":
        polaczenie = smtplib.SMTP_SSL(dane["host"], dane["port"], timeout=TIMEOUT_S, context=ssl.create_default_context())
    else:
        polaczenie = smtplib.SMTP(dane["host"], dane["port"], timeout=TIMEOUT_S)
        if dane["szyfrowanie"] == "starttls":
            polaczenie.starttls(context=ssl.create_default_context())
    polaczenie.login(dane["uzytkownik"], dane["haslo"])
    return polaczenie


def _dane_polaczenia_lub_blad() -> dict:
    dane = email_ustawienia.pobierz_dane_polaczenia_email()
    if dane is None:
        raise BladEmail(
            "Konfiguracja poczty (SMTP) nie jest jeszcze ustawiona - uzupełnij ją w Ustawieniach."
        )
    return dane


def wyslij_email(
    do: str, temat: str, tresc: str, zalaczniki: list[Zalacznik] | None = None
) -> None:
    """Wysyla pojedynczy e-mail tekstowy. Rzuca BladEmail z czytelnym
    komunikatem po polsku - wywolujacy (app/services/przypomnienia_service.py)
    decyduje, czy przerwac cala paczke, czy zapisac blad przy pojedynczej
    pozycji i kontynuowac reszte."""
    dane = _dane_polaczenia_lub_blad()

    wiadomosc = EmailMessage()
    wiadomosc["Subject"] = temat
    wiadomosc["From"] = formataddr((dane.get("nadawca_nazwa") or "", dane["nadawca_adres"]))
    wiadomosc["To"] = do
    wiadomosc.set_content(tresc)
    for zalacznik in zalaczniki or []:
        maintype, _, subtype = zalacznik.typ_mime.partition("/")
        wiadomosc.add_attachment(
            zalacznik.tresc, maintype=maintype or "application", subtype=subtype or "octet-stream",
            filename=zalacznik.nazwa_pliku,
        )

    try:
        polaczenie = _polacz(dane)
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        raise BladEmail(f"Nie udało się połączyć z serwerem SMTP ({dane['host']}:{dane['port']}): {e}") from e

    try:
        polaczenie.send_message(wiadomosc)
    except smtplib.SMTPException as e:
        raise BladEmail(f"Serwer SMTP odrzucił wiadomość: {e}") from e
    finally:
        try:
            polaczenie.quit()
        except smtplib.SMTPException:
            pass


def testuj_polaczenie() -> dict:
    """Loguje sie do serwera SMTP i od razu sie rozlacza (BEZ wysylania
    zadnej wiadomosci) - potwierdza wylacznie, ze host/port/uzytkownik/haslo/
    szyfrowanie sa poprawne. Ten sam wzorzec co
    ksef_service.testuj_polaczenie (Faza 12A) - zwraca wynik zamiast rzucac,
    zeby UI moglo pokazac komunikat inline zamiast okna bledu."""
    try:
        dane = _dane_polaczenia_lub_blad()
    except BladEmail as e:
        return {"powodzenie": False, "komunikat": str(e)}

    try:
        polaczenie = _polacz(dane)
    except smtplib.SMTPAuthenticationError as e:
        return {"powodzenie": False, "komunikat": f"Serwer SMTP odrzucił dane logowania: {e}"}
    except (smtplib.SMTPException, OSError, TimeoutError) as e:
        return {
            "powodzenie": False,
            "komunikat": f"Nie udało się połączyć z serwerem SMTP ({dane['host']}:{dane['port']}): {e}",
        }

    try:
        polaczenie.quit()
    except smtplib.SMTPException:
        pass
    return {"powodzenie": True, "komunikat": "Połączenie z serwerem SMTP działa poprawnie."}
