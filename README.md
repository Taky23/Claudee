# Szintlépő angol

Írásos angolgyakorló webapp magyar felülettel. Felméri a szintedet (A1–C2), és a gyakorló feladatokat ehhez igazítja. Mikrofon nem kell, minden feladat írásos.

## Használat

Nyisd meg az `index.html` fájlt egy böngészőben. Telepíteni és buildelni nem kell semmit.

## Funkciók

- **Adaptív szintfelmérő:** 15 kérdés. Jó válasz után nehezebb, rossz után könnyebb kérdés jön.
- **Szinthez igazított gyakorlás:** 10 feladatos körök. Ha sorozatban jól válaszolsz, nehezebb feladatot kapsz, ha hibázol, könnyebbet.
- **Szintmérő:** ha a saját szinteden jól teljesítesz, megtelik, és szintet lépsz. Ha sokat hibázol, visszalépsz egy szintet.
- **Ötféle feladat:** feleletválasztós, kiegészítés, fordítás magyarról angolra, mondatépítés szókártyákból és szövegértés.
- **Rugalmas javítás:** elfogadja a rövidített alakokat (*I'm = I am*), és az apró elírásokat is jónak számítja, de jelzi őket.
- **Magyar nyelvű magyarázat** minden feladat után.
- **Hibafüzet:** a rontott feladatok visszajönnek. Ha kétszer egymás után eltalálod, kikerülnek.
- **Motiváció:** XP, napi cél (20 feladat), napos sorozat és készségenkénti statisztika.
- **Segítség gomb:** feleletválasztósnál kiveszi két rossz választ, beírósnál megmutatja a szavak kezdőbetűit. Ilyenkor fele annyi XP jár.

A haladásod a böngésződ helyi tárolójában (localStorage) marad meg.

## Feladatbank

Az `index.html` elején lévő `BANK` tömbben szintenként 14 feladat van, összesen 84. Új feladatot úgy adhatsz hozzá, hogy felveszel egy újabb objektumot (`l`: szint 0–5, `s`: készség, `t`: típus, `a`: helyes válasz(ok), `x`: magyarázat).
