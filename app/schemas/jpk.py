from pydantic import BaseModel


class ProblemFakturyJPK(BaseModel):
    faktura_id: int
    numer: str
    klient_nazwa: str
    # "robocza" - faktura nie zostala jeszcze wystawiona (brak mocy prawnej,
    # nie moze wejsc do ewidencji); "brak_nip_klienta" - kontrahent bez NIP
    # (dopuszczalne w JPK jako "brak", ale zwykle oznacza brakujace dane klienta).
    problem: str


class GotowoscOkresuJPK(BaseModel):
    liczba_faktur_do_ujecia: int
    problemy: list[ProblemFakturyJPK]


class UrzadSkarbowyOut(BaseModel):
    kod: str
    nazwa: str
