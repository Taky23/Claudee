# 📚 EPUB Fordító (Windows)

Egyszerű asztali program e-könyvekhez:

- **EPUB → TXT**: kinyeri a könyv szövegét (fejezetenként, bekezdésekkel).
- **TXT → EPUB**: szövegfájlból rendes e-könyvet készít (címlap, fejezetek, tartalomjegyzék). A fejezeteket a 3 üres sorból vagy a „Chapter 1”, „1. fejezet”, „Prológus” stb. sorokból ismeri fel.
- **Fordítás angolról magyarra (DeepL)**: EPUB-ot vagy TXT-t fordít. EPUB-nál a könyv **szerkezete megmarad**: fejezetek, dőlt és félkövér betűk, linkek, képek, tartalomjegyzék. Az eredmény egy új, `… - magyar.epub` fájl.
  - **Magyar idézőjelek**: a `"…"` jelekből `„…”` lesz (kikapcsolható).
  - A könyv címét és a tartalomjegyzéket is lefordítja (kikapcsolható).
  - **Folytatható**: a már lefordított bekezdéseket elmenti a gépen. Ha megszakad, vagy elfogy a havi keret, legközelebb onnan folytatja, és nem küldi el (nem számolja el) újra ugyanazt a szöveget.

## Letöltés

A legfrissebb **EpubFordito.exe** itt van: [Releases → EPUB Fordító](../../releases/tag/epub-fordito).
Nem kell telepíteni, csak elindítani.

> Mivel a program nincs digitálisan aláírva, az első indításnál a Windows figyelmeztethet („A Windows megvédte a számítógépet”). Ilyenkor: **További információ → Futtatás mindenképp**.

## DeepL-kulcs (ingyenes)

1. Regisztrálj a <https://www.deepl.com/pro-api> oldalon a **DeepL API Free** csomagra (havi 500 000 karakter ingyen, ami kb. 1–2 regény).
2. A fiókodban a **„API Keys”** résznél másold ki a kulcsot (`…:fx` a vége).
3. Illeszd be a programba (2. lépés), és nyomd meg a **Mentés** gombot. A **Keret** gomb megmutatja, mennyi karaktered maradt a hónapban.

A kulcs csak a saját gépeden tárolódik (`%APPDATA%\EpubFordito\config.json`). A könyv szövege csak a DeepL-hez megy ki fordításra.

## Parancssor (haladóknak)

```
EpubFordito.exe to-txt   konyv.epub
EpubFordito.exe to-epub  konyv.txt --title "Cím" --author "Szerző"
EpubFordito.exe translate konyv.epub --key DEEPL_KULCS
EpubFordito.exe usage
```

Forrásból: `pip install lxml`, majd `python epub_fordito.py`. Tesztek: `pytest desktop/epub-fordito`.
