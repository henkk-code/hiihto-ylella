# Hiihto Ylellä – projektisuunnitelma (v0.4)

*Päivitetty 2026-11-21. Tila: **vaiheet 1 ja 4 (pistetilanne) julkaistu** → https://henkk-code.github.io/hiihto-ylella/*

**Nykytila (20.11.2026):** Ylen suorat lähetykset kellonaikoineen (Telkku), kauden Yle-tapahtumat (Ylen lista) ja FIS-kisaohjelma. Maastohiihdon maailmancupin kisat, joita Yle ei näytä (Davos, Tour de Ski, Engadin, Oslo, Drammen), näkyvät kauden listalla harmaina ("Ei Ylellä"). Vaihe 2 on peruttu. Mahdollinen jatko on vaihe 3 (muut lajit/kanavat).

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
                                       tallenna viim. onnistunut
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

**Vaihe 2 – ~~Kisat, Falun ja kalenteri~~ PERUTTU 20.11.2026** (käyttäjän päätös)
- FIS-kisat tapahtumien alle ja Falunin MM-ohjelma (maastohiihto + yhdistetyn hiihto-osuudet): ✅ tehty jo MVP:ssä
- ~~Tilattava kalenteri (.ics)~~: ei tarvita
- ~~Ampumahiihdon kisatason lähde (IBU)~~: ei tehdä

Huom: Tour de Ski (vuodenvaihde) on osa maailmancupia, mutta Ylen kausilistan mukaan sitä ei näytetä Ylellä
(vain Viaplay), joten se ei ole sivulla. Jos Yle myöhemmin näyttää sen, lisätään tapahtuma `events.json`iin
kentällä `"tour_de_ski": true`. Muuten TV-oppaan otsikoista poistetaan virheellinen "Tour de Ski" -merkintä
(esim. Rukan maailmancup).

**Vaihe 3 – Laajennus** (tarpeen mukaan)
- Muut lajit Ylen listalta (alppihiihto ym.) ja muut ilmaiskanavat (MTV3 ym.) Telkun kautta

**Vaihe 4 – Maailmancupin pistetilanne** (✅ hyväksytty ja toteutettu 21.11.2026)

Tavoite: kun kisat alkavat (hiihto Ruka 27.11., ampumahiihto Kontiolahti 26.11.), sivulta näkee yhdellä silmäyksellä, kuka johtaa maailmancupia.

- **Paikka:** kolmas välilehti **Maailmancup** laskurin kanssa (laskuri = näkyvien pistelistojen määrä valituilla lajeilla). Välilehti näkyy vasta, kun kauden ensimmäinen kisa on ajettu. Vastauslaatikkoon ei lisätä mitään, joten sivun ensisijainen kysymys pysyy ylimpänä.
- **Sisältö:** yksi GitHub-laatikko per laji ja sarja (Hiihto M/N, Ampumahiihto M/N, Yhdistetty M/N). Otsikkorivillä "Kokonaiskilpailu · 4/32 kisaa". Kärkiviisikko pisteineen, johtajalla keltainen "Johtaa"-pilleri ja ero kakkoseen ("+45 p"). Jos paras suomalainen ei ole kärkiviisikossa, hänet näytetään erotinviivan alla omalla rivillään (esim. "12. NISKANEN Iivo 180 p"). Lajisuodatin koskee myös tätä välilehteä.
- **Päivitys:** sama 1×/vrk Actions-ajo kuin muillakin lähteillä. Jos haku epäonnistuu, näytetään edellinen tallennettu tilanne ja sen päivämäärä.
- **Lähteet** (ks. [DATALAHTEET.md §5](DATALAHTEET.md)):
  - Hiihto ja yhdistetty: FIS:n viralliset cup-standings-sivut (HTML). Testattu: kauden 2025–26 lopputilanne jäsentyy (KLAEBO 2 301 p …).
  - Ampumahiihto: IBU:n rajapinta on suljettu (401). Ehdotus: englanninkielisen Wikipedian kausisivu "2026–27 Biathlon World Cup", jolla on Standings-taulukot, ja linkki biathlonworld.comiin. Vaihtoehto: ampumahiihto jätetään pois ja tilalle pelkkä linkki.
- **Työmäärä:** FIS-jäsennin, testit tallennetulla sivulla ja välilehti noin 0,5 pv. Ampumahiihto Wikipediasta +2–3 h.

Päätökset 21.11.2026 (suositukset hyväksytty):
1. Ampumahiihdon lähde on Wikipedia. Siellä on vain kärkikymmenikkö, joten paras suomalainen näkyy vain, jos hän on kymmenen joukossa.
2. Yhdistetty on mukana (koko cupin pisteet, mäki + hiihto).
3. Vain kokonaiskilpailu. Matka- ja sprintticup lisätään tarvittaessa.

### Arvio: kärkiurheilijoiden profiilit (FIS + Wikipedia) – EI TOTEUTETA VIELÄ

**Mitä datasta saa (testattu 21.11.2026, Iivo Niskanen):**

| Lähde | Antaa | Huom. |
|---|---|---|
| **Wikidata** (avoin API, SPARQL) | syntymäaika, -paikka, seura, kuva (Commons), **FIS-tunniste P2773** | Avainlöydös: P2773 = FIS:n `competitorid` (Iivolla 150212 → oikea FIS-sivu). Tunniste löytyy 4 001 hiihtäjältä. Nimien sovitusta "NISKANEN Iivo" ↔ "Iivo Niskanen" ei siis tarvita. |
| **Wikipedia fi** (REST `page/summary`) | 1–3 lauseen ingressi ja pikkukuva | Lisenssi CC BY-SA, joten lähde ja linkki on mainittava. Kuvien lisenssit vaihtelevat (Commons). |
| **FIS-urheilijasivu** (HTML) | FIS-koodi, seura, välineet (sukset, monot, sauvat), harrastukset, FIS-pisteet, tuloslista suodattimin | Jäsennettävä HTML-sivu, joka voi muuttua. Tuloshistoria vaatii useita sivulatauksia per urheilija. |
| **IBU** | – | Rajapinta suljettu. Ampumahiihtäjistä saa vain Wikidata- ja Wikipedia-tiedot, ei tulostilastoja. |

**Vaiva kolmessa tasossa:**

| Taso | Sisältö | Työ | Ylläpito |
|---|---|---|---|
| **A. Kevyt** | Pistetilanteen rivi aukeaa: kuva, ikä, seura, Wikipedia-ingressi, linkit FIS:iin ja Wikipediaan, sijoitus cupissa | ~0,5–1 pv (vaiheen 4 päälle) | Pieni. Urheilijalista syntyy automaattisesti pistetilanteen kärjestä, ja Wikidata hakee loput. |
| **B. Tilastot** | + uran MC-voitot ja -palkintosijat, kauden kisat sijoituksineen (FIS-tuloslista) | +1–2 pv | Keskisuuri. FIS-sivujen jäsennin hajoaa sivumuutoksissa. Vain hiihto ja yhdistetty. |
| **C. Omat profiilisivut** | Erillinen sivu per urheilija, kuvaajat, vertailut | 3–5 pv | Suuri. Ei sovi kertasilmäyssivun luonteeseen (CLAUDE.md). |

**Suositus:** taso A pistetilanteen jatkeeksi. Data kulkee pistetilanne → FIS-id → Wikidata (SPARQL P2773) → Wikipedia, ja kaikki haetaan buildissa 1×/vrk.
B kannattaa vain, jos A:ta oikeasti käytetään. C ei sovi sivun tarkoitukseen.
Riskit: Wikidatasta voi puuttua tunniste (uudet nuoret hiihtäjät, jolloin näytetään pelkkä nimi ja FIS-linkki), kuvien lisenssimerkinnät ja ampumahiihdon tilastoaukko.

## 5. Hakemistorakenne

```
hiihto/
├── SUUNNITELMA.md, DATALAHTEET.md, README.md
├── data/events.json          # käsin: Ylen kausilista
├── config/
│   ├── sources.json          # FIS-syötteet, Telkun kanavaryhmä ja kanava-id:t
│   └── topics.json           # lajit ja tunnistussäännöt
├── build/
│   ├── build.py              # hae → yhdistä → site/data.json
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
