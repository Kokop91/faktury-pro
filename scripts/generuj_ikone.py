"""Generuje assets/icon.ico (wielorozdzielczy) dla instalatora i pliku .exe -
prosty dokument/faktura na zaokraglonym kwadracie w kolorze akcentu appki
(#3D5AFE, ten sam co gui/styl.py:KOLOR_AKCENT jasny wariant), spojny z
programowo rysowanymi ikonami w gui/ikony.py.

Uzycie (jednorazowe - wynik jest juz zacommitowany w assets/icon.ico,
uruchamiac ponownie tylko przy zmianie wygladu ikony):
    python scripts/generuj_ikone.py
"""
from pathlib import Path

from PIL import Image, ImageDraw

KOLOR_AKCENT = (61, 90, 254, 255)  # #3D5AFE
BIALY = (255, 255, 255, 255)

ROZMIAR_BAZOWY = 256

ROOT = Path(__file__).resolve().parent.parent


def _rysuj(rozmiar: int) -> Image.Image:
    skala = rozmiar / ROZMIAR_BAZOWY
    obraz = Image.new("RGBA", (rozmiar, rozmiar), (0, 0, 0, 0))
    rysuj = ImageDraw.Draw(obraz)

    def s(v):
        return v * skala

    # Tlo: zaokraglony kwadrat w kolorze akcentu.
    rysuj.rounded_rectangle(
        [s(8), s(8), s(248), s(248)], radius=s(56), fill=KOLOR_AKCENT
    )

    # Dokument (faktura) - bialy prostokat z zagietym rogiem i liniami tekstu.
    rysuj.polygon(
        [
            (s(76), s(56)), (s(150), s(56)), (s(180), s(86)),
            (s(180), s(200)), (s(76), s(200)),
        ],
        fill=BIALY,
    )
    rysuj.polygon([(s(150), s(56)), (s(180), s(86)), (s(150), s(86))], fill=(210, 219, 255, 255))

    grubosc = max(1, round(s(6)))
    for y in (110, 132, 154, 176):
        rysuj.line([(s(94), s(y)), (s(162), s(y))], fill=KOLOR_AKCENT, width=grubosc)

    return obraz


def main() -> None:
    docelowy = ROOT / "assets" / "icon.ico"
    docelowy.parent.mkdir(parents=True, exist_ok=True)
    rozmiary = [16, 24, 32, 48, 64, 128, 256]
    obrazy = [_rysuj(r) for r in rozmiary]
    obrazy[-1].save(
        docelowy,
        format="ICO",
        sizes=[(r, r) for r in rozmiary],
    )
    print(f"Zapisano {docelowy}")


if __name__ == "__main__":
    main()
