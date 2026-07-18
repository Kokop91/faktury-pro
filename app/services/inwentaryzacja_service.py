from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    DokumentMagazynowy,
    Inwentaryzacja,
    PozycjaInwentaryzacji,
    Produkt,
    StanMagazynowy,
)
from app.models.enums import StatusInwentaryzacji, TypDokumentuMagazynowego
from app.schemas.inwentaryzacja import (
    AktualizacjaPozycjiInwentaryzacji,
    InwentaryzacjaCreate,
    InwentaryzacjaOut,
    PozycjaInwentaryzacjiOut,
)
from app.schemas.magazyn import DokumentMagazynowyCreate, PozycjaDokumentuMagazynowegoCreate
from app.services import magazyn_service
from app.services.numeracja_inwentaryzacji import nastepny_numer_inwentaryzacji


def _zbuduj_pozycja_out(pozycja: PozycjaInwentaryzacji) -> PozycjaInwentaryzacjiOut:
    return PozycjaInwentaryzacjiOut(
        id=pozycja.id,
        produkt_id=pozycja.produkt_id,
        produkt_nazwa=pozycja.produkt.nazwa,
        jednostka_miary=pozycja.produkt.jednostka_miary,
        stan_systemowy=pozycja.stan_systemowy,
        stan_faktyczny=pozycja.stan_faktyczny,
    )


def zbuduj_inwentaryzacja_out(inwentaryzacja: Inwentaryzacja) -> InwentaryzacjaOut:
    return InwentaryzacjaOut(
        id=inwentaryzacja.id,
        magazyn_id=inwentaryzacja.magazyn_id,
        numer=inwentaryzacja.numer,
        data_rozpoczecia=inwentaryzacja.data_rozpoczecia,
        data_zakonczenia=inwentaryzacja.data_zakonczenia,
        status=inwentaryzacja.status,
        pozycje=[_zbuduj_pozycja_out(p) for p in inwentaryzacja.pozycje],
        utworzono=inwentaryzacja.utworzono,
        zaktualizowano=inwentaryzacja.zaktualizowano,
    )


def otworz_inwentaryzacje(db: Session, dane: InwentaryzacjaCreate) -> Inwentaryzacja:
    magazyn = magazyn_service.pobierz_magazyn(db, dane.magazyn_id)

    istniejaca = db.execute(
        select(Inwentaryzacja).where(
            Inwentaryzacja.magazyn_id == magazyn.id,
            Inwentaryzacja.status == StatusInwentaryzacji.W_TRAKCIE,
        )
    ).scalar_one_or_none()
    if istniejaca is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Magazyn '{magazyn.nazwa}' ma juz otwarty spis ({istniejaca.numer}) - "
                "zamknij go przed otwarciem nowego."
            ),
        )

    produkty_towar = db.execute(
        select(Produkt).where(
            Produkt.jest_magazynowy.is_(True), Produkt.aktywny.is_(True)
        )
    ).scalars().all()

    stany = db.execute(
        select(StanMagazynowy).where(StanMagazynowy.magazyn_id == magazyn.id)
    ).scalars().all()
    ilosc_wg_produktu = {s.produkt_id: s.ilosc for s in stany}

    dzisiaj = date.today()
    numer = nastepny_numer_inwentaryzacji(db, dzisiaj.year)

    inwentaryzacja = Inwentaryzacja(
        magazyn_id=magazyn.id,
        numer=numer,
        data_rozpoczecia=dzisiaj,
        status=StatusInwentaryzacji.W_TRAKCIE,
    )
    db.add(inwentaryzacja)
    db.flush()

    for produkt in produkty_towar:
        db.add(
            PozycjaInwentaryzacji(
                inwentaryzacja_id=inwentaryzacja.id,
                produkt_id=produkt.id,
                stan_systemowy=ilosc_wg_produktu.get(produkt.id, Decimal("0")),
                stan_faktyczny=None,
            )
        )

    db.commit()
    db.refresh(inwentaryzacja)
    return pobierz_inwentaryzacje(db, inwentaryzacja.id)


def pobierz_inwentaryzacje(db: Session, inwentaryzacja_id: int) -> Inwentaryzacja:
    zapytanie = (
        select(Inwentaryzacja)
        .options(
            selectinload(Inwentaryzacja.pozycje).selectinload(
                PozycjaInwentaryzacji.produkt
            )
        )
        .where(Inwentaryzacja.id == inwentaryzacja_id)
    )
    inwentaryzacja = db.execute(zapytanie).scalar_one_or_none()
    if inwentaryzacja is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono spisu inwentaryzacyjnego o podanym id.",
        )
    return inwentaryzacja


def lista_inwentaryzacji(
    db: Session,
    magazyn_id: int | None,
    status_filtr: StatusInwentaryzacji | None,
    skip: int,
    limit: int,
) -> list[Inwentaryzacja]:
    zapytanie = select(Inwentaryzacja)
    if magazyn_id is not None:
        zapytanie = zapytanie.where(Inwentaryzacja.magazyn_id == magazyn_id)
    if status_filtr is not None:
        zapytanie = zapytanie.where(Inwentaryzacja.status == status_filtr)
    zapytanie = zapytanie.order_by(Inwentaryzacja.id.desc()).offset(skip).limit(limit)
    return list(db.execute(zapytanie).scalars().all())


def zapisz_pozycje(
    db: Session, inwentaryzacja_id: int, dane: AktualizacjaPozycjiInwentaryzacji
) -> Inwentaryzacja:
    inwentaryzacja = pobierz_inwentaryzacje(db, inwentaryzacja_id)
    if inwentaryzacja.status != StatusInwentaryzacji.W_TRAKCIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nie mozna edytowac zamknietego spisu.",
        )

    pozycje_wg_produktu = {p.produkt_id: p for p in inwentaryzacja.pozycje}
    for wpis in dane.pozycje:
        pozycja = pozycje_wg_produktu.get(wpis.produkt_id)
        if pozycja is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Produkt o id {wpis.produkt_id} nie jest czescia tego spisu "
                    "(nie byl towarem magazynowym w chwili otwarcia)."
                ),
            )
        pozycja.stan_faktyczny = wpis.stan_faktyczny

    db.commit()
    db.refresh(inwentaryzacja)
    return pobierz_inwentaryzacje(db, inwentaryzacja.id)


def zamknij_inwentaryzacje(
    db: Session, inwentaryzacja_id: int
) -> tuple[Inwentaryzacja, list[DokumentMagazynowy], list[str]]:
    """Finalizuje spis: dla kazdej policzonej pozycji, gdzie stan faktyczny rozni
    sie od systemowego (migawka z otwarcia), generuje korekte PW (nadwyzka) albo
    RW (niedobor) przez magazyn_service.utworz_dokument_magazynowy - a wiec przez
    ta sama, juz sprawdzona logike zmiany stanow z Fazy 8 (numeracja, blokada/
    ostrzezenie ponizej zera). Pozycje bez wpisanego stanu faktycznego (nigdy nie
    policzone) sa pomijane, nie blokuja zamkniecia.

    RW generujemy PRZED PW: RW to jedyny z tych dwoch typow, ktory moze zostac
    odrzucony (tryb "blokuj" przy zejsciu ponizej zera) - robiac go pierwszym,
    ewentualny blad przerywa operacje zanim cokolwiek zostanie zapisane, wiec
    nie ma ryzyka podwojnego naliczenia korekty przy ponownej probie zamkniecia.

    Oba dokumenty tworzone sa z commit=False - RW, PW i zmiana statusu spisu
    na ZAKONCZONA musza trafic do bazy JEDNYM wspolnym db.commit() na koncu tej
    funkcji, inaczej proces przerwany miedzy commitem RW a commitem PW (albo
    miedzy PW a zapisaniem statusu) zostawia spis w stanie W_TRAKCIE z czescia
    korekt juz zapisanych - ponowna proba zamkniecia policzylaby roznice od tej
    samej migawki stan_systemowy/stan_faktyczny i utworzylaby korekty PO RAZ
    DRUGI, podwajajac zmiane stanu.
    """
    inwentaryzacja = pobierz_inwentaryzacje(db, inwentaryzacja_id)
    if inwentaryzacja.status != StatusInwentaryzacji.W_TRAKCIE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Spis jest juz zamkniety.",
        )

    notatka = f"korekta inwentaryzacyjna nr {inwentaryzacja.numer}"
    pozycje_nadwyzka: list[PozycjaDokumentuMagazynowegoCreate] = []
    pozycje_niedobor: list[PozycjaDokumentuMagazynowegoCreate] = []

    for pozycja in inwentaryzacja.pozycje:
        if pozycja.stan_faktyczny is None:
            continue
        roznica = pozycja.stan_faktyczny - pozycja.stan_systemowy
        if roznica > 0:
            pozycje_nadwyzka.append(
                PozycjaDokumentuMagazynowegoCreate(
                    produkt_id=pozycja.produkt_id, ilosc=roznica, notatka=notatka
                )
            )
        elif roznica < 0:
            pozycje_niedobor.append(
                PozycjaDokumentuMagazynowegoCreate(
                    produkt_id=pozycja.produkt_id, ilosc=-roznica, notatka=notatka
                )
            )

    dokumenty_utworzone: list[DokumentMagazynowy] = []
    ostrzezenia: list[str] = []

    if pozycje_niedobor:
        dokument_rw, ostrzezenia_rw = magazyn_service.utworz_dokument_magazynowy(
            db,
            DokumentMagazynowyCreate(
                typ=TypDokumentuMagazynowego.RW,
                data_dokumentu=date.today(),
                magazyn_zrodlowy_id=inwentaryzacja.magazyn_id,
                pozycje=pozycje_niedobor,
            ),
            commit=False,
        )
        dokumenty_utworzone.append(dokument_rw)
        ostrzezenia.extend(ostrzezenia_rw)

    if pozycje_nadwyzka:
        dokument_pw, ostrzezenia_pw = magazyn_service.utworz_dokument_magazynowy(
            db,
            DokumentMagazynowyCreate(
                typ=TypDokumentuMagazynowego.PW,
                data_dokumentu=date.today(),
                magazyn_docelowy_id=inwentaryzacja.magazyn_id,
                pozycje=pozycje_nadwyzka,
            ),
            commit=False,
        )
        dokumenty_utworzone.append(dokument_pw)
        ostrzezenia.extend(ostrzezenia_pw)

    inwentaryzacja.status = StatusInwentaryzacji.ZAKONCZONA
    inwentaryzacja.data_zakonczenia = date.today()
    db.commit()
    db.refresh(inwentaryzacja)

    return pobierz_inwentaryzacje(db, inwentaryzacja.id), dokumenty_utworzone, ostrzezenia
