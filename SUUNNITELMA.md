# Hiihto Ylellä – projektisuunnitelma (v0.3)

*Päivitetty 2026-11-20. Tila: **hyväksytty; vaihe 1 (MVP) julkaistu 20.11.2026** → https://henkk-code.github.io/hiihto-ylella/*

Muutokset v0.2 → v0.3:
- **Kellonajat ja kanava mukaan jo MVP:ssä.** Lähteenä Telkku.comin (Iltalehti) julkinen TV-opasrajapinta. Testattu, toimii, ei avainta.
- Yhdistetystä mukana **hiihto-osuus**, mäkihyppy jätetään pois
- Hosting päätetty: **GitHub Pages + GitHub Actions**

## 1. Tavoite

Julkinen, kevyt web-sivu, joka vastaa ilman googlaamista:

> **"Näyttääkö Yle hiihtoa tai ampumahiihtoa tänä/ensi viikonloppuna – mitä kisoja, mihin aikaan ja millä kanavalla?"**

Lisäksi koko kauden lista: maailmancup (MC), Suomen cup (SC), SM, MM.
Laajennettavissa muihin lajeihin ja muille (ilmais)kanaville. Telkun data kattaa jo MTV3:n, Nelosen, Subin ym.

## 2. Tietolähteet: kolme kerrosta (tarkemmin [DATALAHTEET.md](DATALAHTEET.md))

| Kerros | Antaa | Lähde | Ulottuvuus |
|---|---|---|---|
| **1. Tapahtuma** | Mitkä tapahtumat Yle näyttää (esim. "Ruka MC 27.–29.11.") | Ylen kausilista yle.fi/a/74-20251336, käsin `data/events.json` | koko kausi |
| **2. Kisa** | Yksittäiset kisat päivittäin (esim. "la 28.11. N 10 km C") | FIS:n virallinen iCal-syöte | koko kausi |
| **3. Lähetys** | **Kellonaika, kanava, suora/uusinta** (esim. "la 9.40–10.46 Yle TV2, SUORA") | Telkku.comin TV-opasrajapinta | **~13 vrk eteenpäin** |

**Robustisuus = hallittu heikkeneminen.** Jokainen kerros toimii ilman seuraavaa:
- Telkku kaatuu tai muuttuu → sivu näyttää edelliset tallennetut lähetysajat ja kisapäivät, ei tyhjää
- FIS ei vastaa → tapahtumat (Ylen lista) näkyvät silti
- Ylen lista on staattinen tiedosto repossa, eikä se riipu mistään ulkoisesta

### Miksi Telkku eikä Areena
- **Areenan rajapinta** vaatii Ylen oman web-sovelluksen tunnisteet (ilman niitä HTTP 403). Niiden upottaminen julkiseen sivuun ei ole asiallista.
- **Telkun rajapinta** (`il-telkku-api.prod.il.fi`) on avoin. Ei avainta, ja palvelin sallii selainkutsut mistä tahansa osoitteesta (`Access-Control-Allow-Origin: *`).
  Datassa on valmiina `format: SPORT` ja `broadcastType: live | rerun`. Suorat lähetykset erottuvat siis koosteista ja uusinnoista ilman arvailua.
- Testi 20.11.: la 28.11. Yle TV2:lta löytyivät mm. Rukan sprinttikarsinnat ja -finaalit, Kontiolahden pari- ja sekaviestit sekä yhdistetyn hiihto-osuus. Kaikki kellonaikoineen ja merkittyinä `live`.
- Epävirallinen tämäkin. Siksi haku tehdään harvoin (1×/vrk), data tallennetaan omaan JSONiin, ja sivu toimii ilman sitä (ks. yllä).

**Tunnettu aukko:** pelkät Areena-striimit (esim. osa Suomen cupista) eivät ole TV-oppaissa. Ne näkyvät kisatasolla (FIS) linkillä Areenaan, ilman kellonaikaa.

## 3. Arkkitehtuuri

```
 data/events.json  (käsin)       ─┐
 FIS iCal  (kisapäivät)           ├─> build.py ──> site/data.json ──> site/index.html  ──> GitHub Pages
 Telkku API (lähetysajat, 14 vrk) ─┘   yhdistä, suodata,               (staattinen)
                                       tallenna viim. onnistunut  └──> site/hiihto.ics (vaihe 2)
        ▲
 GitHub Actions: 1×/vrk (+ aina kun events.json muuttuu)
```

- **Ei palvelinta.** Python-build (vain standardikirjasto) ajetaan GitHub Actionsissa, ja tulos julkaistaan GitHub Pagesiin.
- **Lähetysten suodatus Telkusta:** kanavat Yle TV1/TV2 (+ Teema Fem), `format = SPORT`, `broadcastType = live`.
  Otsikossa/kuvauksessa lajin tunniste (maastohiihto, hiihdon …, ampumahiihto, yhdistetty + "km").
  Lajisäännöt `config/topics.json`issa, ja testit oikeilla otsikoilla.
- **Liitos:** lähetys liitetään tapahtumaan päivämäärän ja paikannimen perusteella (esim. "… Ruka" → Ruka MC).
  Liittymätön mutta lajiltaan oikea Ylen suora lähetys näytetään silti omana rivinään, joten mikään ei katoa.
- **Laajennus:** uusi laji = rivi `topics.json`iin. Uusi kanava = kanava-id asetuksiin (Telkun kanavaryhmissä ovat jo MTV3, Nelonen, Sub ym.).

### Tietomalli (luonnos)
```
Event     { id, sport, type: MC|SC|SM|MM, place, start, end, broadcaster: "yle", fis_match{…} }
Race      { event_id, date, discipline: CC|NK, gender, name, fis_url }            // FIS
Broadcast { event_id?, sport, channel: "Yle TV2", start, end, title, description,
            live: true, source: "telkku" }                                        // Telkku
```

## 4. Sivun toiminnallisuus

**Vaihe 1 – MVP** (tavoite **ke 25.11.2026**, ennen Kontiolahtea 26.11.)
- **Vastaus ylimpänä:** "Tänä viikonloppuna Ylellä" ja lähetykset kellonaikoineen ja kanavineen.
  Jos niitä ei ole: "Ei Ylen hiihtolähetyksiä tänä viikonloppuna – seuraava: Trondheim MC 4.–6.12."
- **Tulevat 2 viikkoa:** suorat lähetykset päivittäin (aika, kanava, kisa). Käynnissä oleva lähetys korostetaan.
- **Koko kausi:** tapahtumat aikajärjestyksessä. Kauempana olevista näkyy "lähetysajat julkaistaan n. 2 vk ennen".
- Lajisuodatin: hiihto / ampumahiihto / yhdistetty (hiihto) / kaikki
- Vain suorat (koosteet ja uusinnat pois)
- "Tiedot päivitetty …", lähdelinkit (Yle, FIS, Telkku), linkki Areenaan
- Mobiili ensin, tumma/vaalea teema, suomeksi, ei evästeitä

**Vaihe 2 – Kisat, Falun ja kalenteri** (joulukuun alku)
- FIS-kisat tapahtumien alle (myös kauempana olevat ja Areena-only-kisat ilman kellonaikaa)
- **Falun MM 2027:** maastohiihdon 18 kisaa + yhdistetyn 7 kisaa (mäkihyppy pois)
- Tilattava kalenteri (.ics): Ylen suorat hiihtolähetykset kellonaikoineen suoraan puhelimen kalenteriin
- Ampumahiihdon kisatason lähde (IBU) selvitetään

**Vaihe 3 – Laajennus** (tarpeen mukaan)
- Muut lajit Ylen listalta (alppihiihto ym.) ja muut ilmaiskanavat (MTV3 ym.) Telkun kautta

## 5. Hakemistorakenne

```
hiihto/
├── SUUNNITELMA.md, DATALAHTEET.md, README.md
├── data/events.json          # käsin: Ylen kausilista
├── config/
│   ├── sources.json          # FIS-syötteet, Telkun kanavaryhmä ja kanava-id:t
│   └── topics.json           # lajit ja tunnistussäännöt
├── build/
│   ├── build.py              # hae → yhdistä → site/data.json (+ .ics)
│   ├── sources/fis.py, sources/telkku.py
│   ├── ical.py               # pieni iCal-jäsennin/kirjoittaja (stdlib)
│   └── tests/ (+ fixtures/)  # tallennetut esimerkkivastaukset (FIS, Telkku 28.11.)
├── site/index.html
└── .github/workflows/publish.yml
```

## 6. Päätökset

| # | Asia | Päätös |
|---|---|---|
| 1 | Tietolähteet | ✅ Ylen kausilista + FIS iCal + Telkku (kellonajat). Areena ei. |
| 2 | Julkaisu | ✅ Julkinen, **GitHub Pages + Actions** (ajastettu haku tarvitsee Actionsin; Pages on luonteva pari) |
| 3 | Tekniikka | ✅ Python (stdlib) + puhdas HTML/JS |
| 4 | Lajit | ✅ Hiihto, ampumahiihto, yhdistetyn hiihto-osuus. Mäkihyppy pois. |
| 5 | Koosteet | ✅ Ei näytetä (`broadcastType = live`) |
| 6 | Falun MM | ✅ Maastohiihto + yhdistetty, FIS-syötteestä |

Ei avoimia kysymyksiä. Repo luodaan GitHubiin MVP:n alussa (nimi esim. `hiihto-ylella`), kun hyväksyt.

## 7. Riskit

| Riski | Hallinta |
|---|---|
| Telkun rajapinta muuttuu tai sulkeutuu | Hallittu heikkeneminen (§2). Build ei ylikirjoita viimeisintä hyvää dataa tyhjällä. Varalähteiksi Ylen Teksti-TV API (virallinen, vaatii avaimen) tai muu EPG. |
| Lajitunnistus osuu väärin | Ehto `format = SPORT` + `live` rajaa jo valmiiksi. Tunnistussäännöt ja testit oikeilla otsikoilla. |
| Areena-only-lähetykset puuttuvat | Näkyvät FIS-kisapäivinä + Areena-linkki. Hyväksytty rajaus. |
| Ylen lista muuttuu | `events.json` päivitetään käsin, ja lähde ja päiväys näkyvät sivulla. Telkun lähetykset näkyvät, vaikka listasta puuttuisi tapahtuma. |
| GitHub Actionsin ajastus viivästyy tai pysähtyy (60 vrk inaktiivisuus) | Sivulla näkyy päivitysaika. Ajastus voidaan herättää commitilla. |

## Lähteet
- Ylen talviurheilukausi 2026–27: https://yle.fi/a/74-20251336
- FIS-kalenteri ja iCal-tilaus: https://www.fis-ski.com/DB/cross-country/calendar-results.html
- Telkku.com TV-opas: https://www.telkku.com/
