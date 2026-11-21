# Hiihto Ylellä

Julkinen sivu, josta näkee yhdellä silmäyksellä, **näyttääkö Yle hiihtoa tai ampumahiihtoa tänä viikonloppuna**, ja mihin aikaan.

🔗 https://henkk-code.github.io/hiihto-ylella/

## Mistä tiedot tulevat

| Kerros | Sisältö | Lähde |
|---|---|---|
| Tapahtumat | Mitkä tapahtumat Yle näyttää | [Ylen kausilista](https://yle.fi/a/74-20251336), käsin tiedostossa `data/events.json` |
| Kisat | Kisaohjelma päivittäin | FIS:n virallinen iCal-syöte |
| Lähetykset | Kellonaika, kanava, vain suorat | Telkku.comin TV-opas (~2 vk eteenpäin) |
| Pistetilanne | Maailmancupin kokonaiskilpailun kärki + paras suomalainen | FIS (hiihto, yhdistetty), en.wikipedia (ampumahiihto) |
| Hiihtäjät | Maastohiihdon kärkikymmenikön ja parhaan suomalaisen profiili: kauden MC-tulokset, uran MC-voitot, olympia- ja MM-mitalit, esittely | FIS-urheilijasivut, Wikidata, fi.wikipedia |

Jos FIS tai Telkku ei vastaa, build käyttää edellisen julkaisun tietoja. Sivu ei siis koskaan tyhjene.
Taustat ja päätökset: [SUUNNITELMA.md](SUUNNITELMA.md) ja [DATALAHTEET.md](DATALAHTEET.md).

## Ylläpito

- **Tapahtuma lisätään tai muutetaan:** muokkaa `data/events.json` ja pushaa. Actions julkaisee sivun automaattisesti.
- **Lajitunnistus** (mitkä lähetykset näytetään): `config/topics.json`
- **Kanavat ja FIS-syötteet:** `config/sources.json`. Uudella kaudella vaihda `fis.season` (esim. `2028`) ja päivitä `events.json`. Sama kausi ohjaa pistetilannetta (FIS-sivut ja Wikipedian sivu "2027–28 Biathlon World Cup").
- **Päivitys:** GitHub Actions ajaa buildin kaksi kertaa päivässä, aina pushin jälkeen ja tarvittaessa käsin (Actions → "Päivitä ja julkaise" → Run workflow).

## Paikallisesti

```bash
python3 build/build.py                        # hakee datan → site/data.json
python3 -m unittest discover -s build/tests   # testit
cd site && python3 -m http.server 8000        # http://localhost:8000
```

Vain Pythonin standardikirjasto (3.11+). Ei riippuvuuksia eikä build-työkaluja.

---
Epävirallinen harrastesivu, ei Ylen palvelu.
