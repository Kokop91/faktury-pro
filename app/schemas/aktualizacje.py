from pydantic import BaseModel


class AktualizacjaOut(BaseModel):
    wersja_biezaca: str
    wersja_najnowsza: str
    dostepna_nowsza_wersja: bool
    url_pobierania: str
