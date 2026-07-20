"""dodaj_indeksy_wydajnosciowe_list

Diagnoza wydajnosci list (faktury/klienci/produkty) na danych testowych
(25 000 faktur, ~62 700 pozycji faktur, 5 300 produktow, wygenerowanych
skryptem pomiarowym, NIE czescia tej migracji) pokazala przez
EXPLAIN ANALYZE cztery kolumny, ktore kazdorazowo wymuszaly pelny
sekwencyjny skan (lub sortowanie calej tabeli) zamiast trafienia w
indeks, mimo ze zapytania w app/services/faktury.py:lista_faktur i
app/services/magazyn_service.py:lista_produktow juz poprawnie uzywaja
LIMIT/OFFSET i selectinload (klasyczny problem N+1 NIE wystapil - to
juz bylo zrobione poprawnie). Zmierzone (baza testowa, PostgreSQL,
EXPLAIN ANALYZE, BUFFERS):

- pozycje_faktury.faktura_id (brak indeksu) - selectinload(Faktura.pozycje)
  wykonuje "WHERE faktura_id IN (...)" dla KAZDEGO zaladowania listy
  faktur (nie tylko przy filtrowaniu) - Seq Scan całej tabeli
  pozycje_faktury: 1.5ms przy 12.6k wierszy -> 6.3ms przy 62.7k wierszy
  (liniowy wzrost z rozmiarem calej tabeli pozycji, NIEZALEZNIE od
  rozmiaru strony wynikow).
- faktury.status (brak indeksu) - filtrowanie po malo licznym statusie
  (np. "anulowana", ~2% wierszy) zmuszalo skan wsteczny po indeksie PK
  z odrzuceniem ok. 9600 niepasujacych wierszy zanim znaleziono 200
  pasujacych (1.75ms na 25k faktur, rosnie z rzadkoscia statusu i
  rozmiarem tabeli).
- faktury.klient_id (brak indeksu) - filtrowanie po jednym kliencie
  (parametr klient_id w GET /faktury) wymuszalo Seq Scan CALEJ tabeli
  faktury (2.4ms na 25k wierszy) nawet dla klienta majacego tylko
  29 faktur - koszt rosnie z CALKOWITA liczba faktur, nie z liczba
  faktur tego klienta.
- produkty.nazwa (brak indeksu) - lista_produktow sortuje
  ".order_by(Produkt.nazwa)" - bez indeksu Postgres musi posortowac
  CALA tabele produktow przed zwroceniem pierwszej strony (0.4ms przy
  300 produktach -> 8.3ms przy 5300 produktach).

SWIADOMIE pominiete (sprawdzone, brak dowodu na koniecznosc - "nie
zgaduj"): faktury.data_wystawienia (nieuzywana w WHERE/ORDER BY listy
faktur dzisiaj) i klienci.nazwa (lista_klientow sortuje po Klient.id,
czyli PK - zaden indeks po nazwie nie jest przez to zapytanie uzywany;
wyszukiwanie po nazwie klienta jest dzis wylacznie po stronie GUI, nie
trafia do bazy).

Revision ID: 7f5a554bf78f
Revises: 6017974908ed
Create Date: 2026-07-20 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7f5a554bf78f'
down_revision: Union[str, Sequence[str], None] = '6017974908ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_faktury_klient_id"), "faktury", ["klient_id"])
    op.create_index(op.f("ix_faktury_status"), "faktury", ["status"])
    op.create_index(
        op.f("ix_pozycje_faktury_faktura_id"), "pozycje_faktury", ["faktura_id"]
    )
    op.create_index(op.f("ix_produkty_nazwa"), "produkty", ["nazwa"])


def downgrade() -> None:
    op.drop_index(op.f("ix_produkty_nazwa"), table_name="produkty")
    op.drop_index(op.f("ix_pozycje_faktury_faktura_id"), table_name="pozycje_faktury")
    op.drop_index(op.f("ix_faktury_status"), table_name="faktury")
    op.drop_index(op.f("ix_faktury_klient_id"), table_name="faktury")
