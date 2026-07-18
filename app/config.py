import os

from dotenv import load_dotenv

load_dotenv()

# Prywatna, wbudowana instancja PostgreSQL (Faza 18B) - appka zarzadza nia
# sama (patrz gui/postgres_serwer.py) na tych stalych, gdy DATABASE_URL nie
# jest podane jawnie. Port CELOWO inny niz domyslny 5432, zeby nie kolidowac
# z ewentualnym innym Postgresem juz zainstalowanym na komputerze uzytkownika -
# prywatna instancja ma wlasny, oddzielny katalog danych
# (%LOCALAPPDATA%/FakturyPro/pgsql-data) i nasluchuje wylacznie na 127.0.0.1.
POSTGRES_PRYWATNY_HOST = "127.0.0.1"
POSTGRES_PRYWATNY_PORT = 55432
POSTGRES_PRYWATNY_BAZA = "faktury_pro"
POSTGRES_PRYWATNY_UZYTKOWNIK = "postgres"


def adres_prywatnego_postgresa(nazwa_bazy: str = POSTGRES_PRYWATNY_BAZA) -> str:
    return (
        f"postgresql://{POSTGRES_PRYWATNY_UZYTKOWNIK}@{POSTGRES_PRYWATNY_HOST}:"
        f"{POSTGRES_PRYWATNY_PORT}/{nazwa_bazy}"
    )


# Tryb deweloperski (Etap 1/2, bez zmian): DATABASE_URL podane jawnie w .env
# albo w zmiennej srodowiskowej wskazuje na Postgres, ktorym opiekuje sie
# deweloper recznie. Gdy go brak - appka jest u uzytkownika koncowego i sama
# zarzadza WLASNA, prywatna instancja Postgresa (Faza 18B) na stalych powyzej.
UZYWA_PRYWATNEGO_POSTGRESA = "DATABASE_URL" not in os.environ

DATABASE_URL = os.environ.get("DATABASE_URL") or adres_prywatnego_postgresa()
