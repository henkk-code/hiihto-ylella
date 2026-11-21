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
| Tulokset | Jokaisen ajetun kisan top 30 (Kauden kisat → tapahtuma → "Top 30") | FIS-tulossivut; Suomen cup Hiihtoliiton tulos-PDF:istä |

Jos FIS tai Telkku ei vastaa, build käyttää edellisen julkaisun tietoja. Sivu ei siis koskaan tyhjene.
Taustat ja päätökset: [SUUNNITELMA.md](SUUNNITELMA.md) ja [DATALAHTEET.md](DATALAHTEET.md).

## Ylläpito

- **Tapahtuma lisätään tai muutetaan:** muokkaa `data/events.json` ja pushaa. Actions julkaisee sivun automaattisesti.
- **Suomen cupin tulokset:** SC-tapahtumalle kenttä `results_page` = Hiihtoliiton tapahtumasivu (esim. `https://hiihtoliitto.fi/tapahtumat/suomen-cup/ruka/`). Build poimii sivulta tulos-PDF:t. Lisäksi `live_results` = EQ Eventsin live-tulospalvelu (esim. `https://live.time4results.com/hiihto/2027/ruka/`), josta haetaan sprintin finaaliajat.
- **Lajitunnistus** (mitkä lähetykset näytetään): `config/topics.json`
- **Kanavat ja FIS-syötteet:** `config/sources.json`. Uudella kaudella vaihda `fis.season` (esim. `2028`) ja päivitä `events.json`. Sama kausi ohjaa pistetilannetta (FIS-sivut ja Wikipedian sivu "2027–28 Biathlon World Cup").
- **Päivitys:** GitHub Actions ajaa buildin kaksi kertaa päivässä (5.20 ja 15.20), kisapäivinä (MC, MM, SC, SM) myös klo 22.20, aina pushin jälkeen ja tarvittaessa käsin (Actions → "Päivitä ja julkaise" → Run workflow).

## Paikallisesti

```bash
python3 build/build.py                        # hakee datan → site/data.json
python3 -m unittest discover -s build/tests   # testit
cd site && python3 -m http.server 8000        # http://localhost:8000
```

Vain Pythonin standardikirjasto (3.11+). Suomen cupin tulos-PDF:ien lukemiseen tarvitaan `pdftotext` (paketti `poppler-utils`); ilman sitä muu sivu rakentuu normaalisti.

---
Epävirallinen harrastesivu, ei Ylen palvelu.
