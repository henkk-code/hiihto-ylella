# Hiihto Ylellä – projektisuunnitelma (v0.7)

*Päivitetty 2026-11-21. Tila: **vaiheet 1, 4 (pistetilanne) ja 5 (hiihtäjäprofiilit) toteutettu** → https://henkk-code.github.io/hiihto-ylella/*

**Nykytila (20.11.2026):** Ylen suorat lähetykset kellonaikoineen (Telkku), kauden Yle-tapahtumat (Ylen lista) ja FIS-kisaohjelma. Maastohiihdon maailmancupin kisat, joita Yle ei näytä (Davos, Tour de Ski, Engadin, Oslo, Drammen), näkyvät kauden listalla harmaina ("Ei Ylellä"). Vaihe 2 on peruttu. Mahdollinen jatko on vaihe 3 (muut lajit/kanavat).

Muutokset v0.6 → v0.7:
- **Vaihe 6b – Erot voittajaan** hyväksytty 21.11.2026 ja toteutettu, ks. §4: sprintin finalisteille (sijat 1–6) finaalin aika ja ero voittajaan.

Muutokset v0.5 → v0.6:
- **Vaihe 6 – Kisojen top 30 -tulokset** hyväksytty suosituksin 21.11.2026 ja toteutettu, ks. §4.

Muutokset v0.4 → v0.5:
- **Vaihe 5 – Hiihtäjäprofiilit (taso B, vain maastohiihto)**, ks. §4: kärkikymmenikkö + paras suomalainen, ei kuvia, olympia- ja MM-mitalit emojeina. Tason A/B/C-arvio korvattu tällä.

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
 GitHub Actions: 2×/vrk (5.20, 15.20) + 22.20 MC/MM-kisapäivinä (+ aina kun repo muuttuu)
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
- Kaikki urheilu ilmaiskanavilla + Disney+ omalle sivulle, ks. [SUUNNITELMA-URHEILU.md](SUUNNITELMA-URHEILU.md) (v0.2, hyväksytty 21.11.2026, ei vielä toteutettu)

**Vaihe 4 – Maailmancupin pistetilanne** (✅ hyväksytty ja toteutettu 21.11.2026)

Tavoite: kun kisat alkavat (hiihto Ruka 27.11., ampumahiihto Kontiolahti 26.11.), sivulta näkee yhdellä silmäyksellä, kuka johtaa maailmancupia.

- **Paikka:** kolmas välilehti **Maailmancup** laskurin kanssa (laskuri = näkyvien pistelistojen määrä valituilla lajeilla). Välilehti näkyy vasta, kun kauden ensimmäinen kisa on ajettu. Vastauslaatikkoon ei lisätä mitään, joten sivun ensisijainen kysymys pysyy ylimpänä.
- **Sisältö:** yksi GitHub-laatikko per laji ja sarja (Hiihto M/N, Ampumahiihto M/N, Yhdistetty M/N). Otsikkorivillä "Kokonaiskilpailu · 4/32 kisaa". Kärkiviisikko pisteineen, johtajalla keltainen "Johtaa"-pilleri ja ero kakkoseen ("+45 p"). Jos paras suomalainen ei ole kärkiviisikossa, hänet näytetään erotinviivan alla omalla rivillään (esim. "12. NISKANEN Iivo 180 p"). Lajisuodatin koskee myös tätä välilehteä.
- **Päivitys:** samat Actions-ajot kuin muillakin lähteillä (5.20 ja 15.20) sekä MC- ja MM-kisapäivinä iltapäivitys 22.20 (`build/raceday.py` tarkistaa kisapäivän julkaistusta datasta ja ohittaa muut päivät). Jos haku epäonnistuu, näytetään edellinen tallennettu tilanne ja sen päivämäärä.
- **Lähteet** (ks. [DATALAHTEET.md §5](DATALAHTEET.md)):
  - Hiihto ja yhdistetty: FIS:n viralliset cup-standings-sivut (HTML). Testattu: kauden 2025–26 lopputilanne jäsentyy (KLAEBO 2 301 p …).
  - Ampumahiihto: IBU:n rajapinta on suljettu (401). Ehdotus: englanninkielisen Wikipedian kausisivu "2026–27 Biathlon World Cup", jolla on Standings-taulukot, ja linkki biathlonworld.comiin. Vaihtoehto: ampumahiihto jätetään pois ja tilalle pelkkä linkki.
- **Työmäärä:** FIS-jäsennin, testit tallennetulla sivulla ja välilehti noin 0,5 pv. Ampumahiihto Wikipediasta +2–3 h.

Päätökset 21.11.2026 (suositukset hyväksytty):
1. Ampumahiihdon lähde on Wikipedia. Siellä on vain kärkikymmenikkö, joten paras suomalainen näkyy vain, jos hän on kymmenen joukossa.
2. Yhdistetty on mukana (koko cupin pisteet, mäki + hiihto).
3. Vain kokonaiskilpailu. Matka- ja sprintticup lisätään tarvittaessa.

**Vaihe 5 – Hiihtäjäprofiilit, taso B** (✅ hyväksytty muutoksin ja toteutettu 21.11.2026)

Tavoite: Maailmancup-välilehdellä hiihtäjän rivi aukeaa, ja siitä näkee yhdellä silmäyksellä, kuka hän on ja miten hänen kautensa ja uransa ovat menneet. **Vain maastohiihto.** Yhdistetyssä ja ampumahiihdossa nimi on edelleen linkki lähteeseen.

**Kenelle:** hiihdon pistetilanteen kärkikymmenikkö ja paras suomalainen kummassakin sarjassa, eli enintään 22 hiihtäjää. Laatikossa näkyy oletuksena kärkiviisikko, ja alalaidan nappi "Näytä sijat 6–10" avaa loput (kaikissa lajeissa). Lista seuraa pistetilannetta automaattisesti: kun kärkikymmenikköön nousee uusi hiihtäjä, hänen profiilinsa haetaan seuraavassa ajossa, ja pudonneen profiili poistuu.

**Rivillä** (aina näkyvissä, jos mitaleja on): olympia- ja MM-mitalit emojeina, esim. "Olympia 🥇3 🥈1 🥉1 · MM 🥇1 🥈1 🥉2". Lajia ei eritellä. Viestit ja parisprintit lasketaan mukaan.

**Avautuvassa profiilissa** (saman laatikon sisällä, ei kuvia):
- ikä, seura (FIS) ja syntymäpaikka (Wikidata)
- 1–2 virkkeen ingressi suomenkielisestä Wikipediasta ja maininta "Wikipedia, CC BY-SA". Jos fi-artikkelia ei ole, ingressiä ei näytetä.
- uran MC-voitot ja -palkintosijat (henkilökohtaiset, Tour de Skin osakilpailut mukana)
- kauden MC-kisat sijoituksineen: kuusi uusinta ja linkki "Kaikki N kisaa ↗" FIS:iin. Palkintosijoille 🥇🥈🥉.
- linkit: FIS-profiili ↗ ja Wikipedia ↗
- Nimen tai rivin klikkaus tai Enter avaa ja sulkee profiilin. Vain yksi profiili on auki kerrallaan.

**Datan kulku** (kaikki buildissa, `build/sources/athletes.py`):

| # | Lähde | Haku | Antaa |
|---|---|---|---|
| 1 | Pistetilanne (jo olemassa) | – | FIS `competitorid` rivin linkistä |
| 2 | FIS `athlete-biography.html?…&type=result&categorycode=WC&seasoncode=2027` | 1 / hiihtäjä | kauden MC-tulokset, seura, syntymäaika |
| 3 | FIS `…&type=podiums` | 1 / hiihtäjä | MC-palkintosijat kausittain → uran summat |
| 4 | FIS `…&type=result&categorycode=OWG` ja `WSC` (kaikki kaudet) | 2 / hiihtäjä | olympia- ja MM-mitalit (sijat 1–3) |
| 5 | Wikidata SPARQL, `P2773` = FIS-id | 1 kysely kaikille | syntymäpaikka, fi-Wikipedia-artikkeli |
| 6 | fi.wikipedia REST `page/summary` | 1 / hiihtäjä (jos artikkeli on) | ingressi |

Testattu 21.11.2026: Iivo Niskasella olympialaisista 3 kultaa, 1 hopea ja 1 pronssi (parisprintti 2014 mukana), MM-kisoista 1–1–2, MC-uralla 10 voittoa ja 26 palkintosijaa. Klæbolla 103 MC-voittoa. Kauden 2025–26 kärkikymmeniköillä (21 hiihtäjää) tuli 84 FIS-hakua ilman virheitä, ja fi-artikkeli löytyi 20 hiihtäjältä.

**Päivitystahti:** tulokset ja ura haetaan uudelleen, kun hiihtäjän MC-pisteet muuttuvat tai tieto on yli viikon vanha. Mitalit haetaan kerran viikossa ja MM-kisojen aikana (± 1 pv) joka ajossa. FIS-hakujen välissä on 1 sekunnin tauko. Jos haku epäonnistuu, käytetään edellistä profiilia, ja alalaidan tilarivillä näkyy "profiilit: ei päivittynyt".

**Hallittu heikkeneminen:**
- Wikidatasta puuttuu FIS-tunniste: FIS-tiedot ja mitalit näytetään, ingressi ja syntymäpaikka jäävät pois.
- FIS-sivun rakenne muuttuu: jäsennin nostaa virheen, testit tallennetuilla sivuilla huomaavat sen, ja sivulla näytetään edellinen profiili.

Päätökset 21.11.2026:
1. Kuvia ei näytetä (ehkä myöhemmin).
2. Profiili tehdään kärkikymmenikölle ja parhaalle suomalaiselle.
3. Ingressi vain suomenkielisestä Wikipediasta, ei englanninkielistä varalähdettä.
4. Lisäys: olympia- ja MM-mitalit emojeina riville.

**Vaihe 6 – Kisojen top 30 -tulokset** (✅ hyväksytty 21.11.2026, toteutettu)

Tavoite: jokaisen ajetun kisan 30 parasta näkee sivulta yhdellä klikkauksella, myös Suomen cupissa (esim. Rukan SC-sprintit 21.11.).

**Paikka:** Kauden kisat → tapahtuma auki → kisarivin perässä pieni toissijainen nappi "Top 30". Napista aukeaa tuloslista kisarivin alle saman tapahtuman sisään. Vain yksi lista kerrallaan on auki. Nappi näkyy vain, kun tulokset ovat olemassa. Vastauslaatikkoon ei lisätä mitään.

**Tuloslistan rivi:** sija, nimi, maa (MC/MM) tai seura (SC/SM) sekä aika ja ero voittajaan ("+27,0"). Sprintissä näytetään sija ja vaihe (Finaali / Välierä / Erä). Suomalaiset lihavoidaan kansainvälisissä kisoissa. Palkintosijoille 🥇🥈🥉. Alalaidassa linkki koko tuloslistaan (FIS tai PDF ↗).

**Lähteet** (testattu 21.11.2026):

| Kisat | Lähde | Huom. |
|---|---|---|
| MC, MM, Tour de Ski, SM (jos FIS:n kalenterissa) | FIS `results.html?sectorcode=CC&raceid=…`. `raceid` on jo valmiina kisarivin linkissä (iCal). | Sama HTML-rakenne kuin pistetilanteessa ja profiileissa. Lahden 10 km 2026 jäsentyi (88 riviä: sija, nimi, maa, aika, ero). |
| Suomen cup | Hiihtoliiton tapahtumasivun tulos-PDF:t (esim. `hiihtoliitto.fi/tapahtumat/suomen-cup/ruka/`) | Suomen cup ei ole FIS:n kalenterissa lainkaan. PDF:t tekee EQ Timing, ja kolme eri tapahtuman PDF:ää (Ruka-sprintti 2026, Tampere 15 km, Rovaniemi 20 km) ovat samaa muotoa: sija, numero, lisenssi, nimi ja seura. Rukan tämänpäiväiset sprinttitulokset ovat jo sivulla. |

Hylätyt: tapahtumien live-tulospalvelut (esim. `live.time4results.com/hiihto/2027/ruka`) ovat tapahtumakohtaisia, käsin tehtyjä sivuja eivätkä sisällä sprintin lopputulosta yhtenä listana.

**Toteutus:**
- FIS: uusi jäsennin `results.py` ja haku ajetuille kisoille. Tulos haetaan uudelleen vielä 2 vuorokautta kisan jälkeen (korjaukset), sen jälkeen se jäädytetään edellisestä datasta. Kauden aikana noin 85 FIS-kisaa, mutta yhdessä ajossa haetaan vain tuoreet, eli 0–8 sivua.
- Suomen cup: `events.json`:n SC-tapahtumiin uusi kenttä `results_page` (Hiihtoliiton tapahtumasivu, koska osoitteet eivät noudata yhtä kaavaa). Build hakee sivulta tulos-PDF:t (nimessä `lopputulokset` tai `res`, ei `karsinta` eikä `pistetilanne`), lukee ne `pdftotext`illä ja tunnistaa kisan PDF:n otsikosta ("Miehet Sprintti (P)", päivä). Kisat lisätään tapahtuman kisalistaan, vaikka FIS:ssä niitä ei ole.
- `pdftotext` (poppler-utils) asennetaan Actions-ajoon yhdellä rivillä. Pythonin puolella ei tule riippuvuuksia.
- Jos PDF:n jäsennys epäonnistuu, kisariville tulee pelkkä linkki "Tulokset (PDF) ↗", joten käyttäjä pääsee silti tuloksiin.
- Data: noin 30 riviä per kisa `data.json`:ssa, koko kaudelta arviolta 150–200 kt. Testiaineistoksi tallennetaan FIS-tulossivu ja kolme SC-PDF:ää.

**Työmäärä:** noin 1 pv (FIS-osuus 2–3 h, SC-PDF:t ja Hiihtoliiton sivu 3–4 h, käyttöliittymä 2 h).

**Avoimet kysymykset (suositus ensin):**
1. **Sprintit:** ✔ Näytetään vain lopputulokset, joissa on kaikkien sija, myös karsiutuneiden. Karsintariville ei tule omaa listaa. Vaihtoehto: myös karsinnan top 30 erikseen.
2. **Iltapäivitys:** ✔ Lisätään SC- ja SM-kisapäivät klo 22.20 ajoon. Muuten iltapäivän matkakisojen tulokset näkyvät vasta seuraavana aamuna. Lisäkustannusta ei ole, ajo tehdään vain kisapäivinä.
3. **Mitkä kisat:** ✔ Kaikki Kauden kisat -listan kisat, myös harmaat (ei Ylellä), kuten Tour de Ski. Vaihtoehto: vain Ylen näyttämät.

Päätökset 21.11.2026: kaikki kolme suositusta hyväksyttiin.

Toteutuksessa tarkentui:
- FIS merkitsee sprintin vaiheet tulossivulle väliotsikoin (Final / Semifinal / 1/4 Final), ja Hiihtoliiton PDF:issä vaihe on omassa sarakkeessaan. Vaihe näytetään vaiheen ensimmäisellä rivillä.
- Viesteissä ja parisprinteissä näytetään joukkue ja osuuksien hiihtäjät (sukunimet). Mukana ovat myös Suomen cupin viestit (esim. Vuokatti 1.11.).
- Yhdistetyn kisoista näytetään hiihto-osuuden lopputulos (sama FIS-tulossivu).
- Hiihtoliiton sivuilla on rikkinäisiä PDF-linkkejä (404 tai HTML-sivu). Ne ohitetaan hiljaa. Sivuja käytetään uudelleen vuodesta toiseen, joten PDF hyväksytään vain, jos sen päivä osuu tapahtuman päiville.
- Puuttuvia SC-tuloksia etsitään vielä 30 päivää tapahtuman jälkeen.
- Vain kuluvan kauden tulokset (käyttäjän päätös 21.11.2026): raja on Ylen kausilistan ensimmäisen tapahtuman alku, kaudella 2026–27 siis 31.10.2026. Sitä vanhempia tuloksia ei haeta eikä näytetä, eivätkä ne jää myöskään edellisestä datasta.

**Vaihe 6b – Erot voittajaan** (✅ hyväksytty 21.11.2026, toteutettu)

Toive: matkoilla kärkikymmenikölle ja sprinteissä finalisteille (1–6) ero voittajaan sekunteina.

- **Matkat:** ero näkyy jo kaikille top 30 -riveille, sekä FIS:n että Suomen cupin tuloksissa (esim. "+22.1", "+1:03.8"). Muutosta ei tarvita.
- **Sprintit:** tulossivuilla ei ole finaalin aikoja, vain sijat ja vaiheet. Ajat saadaan näin (testattu 21.11.2026):

| Kisat | Lähde | Sisältö |
|---|---|---|
| MC, MM, Tour de Ski, SM | FIS-tulossivun "Results"-PDF (latauslinkki samalla sivulla) | Finaalin sarake: voittajan aika ja muiden erot (Toblach 28.12.2025: Klæbo 2:28.82, Heggen +0.13 …) |
| Suomen cup | EQ Eventsin live-tulospalvelu `live.time4results.com/hiihto/2027/{paikka}/`, finaalin maalisivu | Ruka 21.11.: Vuorinen 2:34.88, Liekari +2.11 … +4.61. Sama rakenne myös Vuokatissa. |

- Live-tulospalvelu hylättiin vaiheessa 6 tuloslistan lähteenä, mutta finaalin maalilista on siellä yksiselitteinen taulukko (sija, numero, nimi, seura, aika, ero). Sitä käytetään vain finaaliaikojen täydentämiseen, ja hiihtäjä yhdistetään PDF-tulokseen kilpailunumerolla.
- `events.json`: SC-tapahtumiin uusi kenttä `live_results` (osoite ei noudata Hiihtoliiton sivun kaavaa).
- Jos aikoja ei saada, lista näytetään kuten nyt, ilman finaaliaikoja.
- Näkymä: finalisteilla sama aika/ero-sarake kuin matkoilla (voittajalla aika, muilla "+2.11"). Vaihe ("Finaali") säilyy.
- Työmäärä noin 2–3 h.

**Avoin kysymys:** yli minuutin erot näytetään nyt muodossa "+1:03.8" (kuten FIS ja Hiihtoliitto). ✔ Suositus: pidetään. Vaihtoehto: aina sekunteina ("+63.8").

Päätös 21.11.2026: hyväksytty, nykyinen muoto pidetään.

Toteutuksessa tarkentui:
- Live-palvelun etusivun otsikosta tarkistetaan tapahtuman alkupäivä ja vuosi, koska osoitteessa on kausi (`/2027/`) ja edellisen kauden sivu voi jäädä voimaan.
- Jo jäädytetyt SC-tulokset haetaan kerran uudelleen, jos finaaliajat puuttuvat (enintään 30 päivää tapahtuman jälkeen). Näin Vuokatin sprintit saivat ajat jälkikäteen.
- Mobiilissa sprintin vaihe näkyy pienenä väliotsikkona, jotta nimet mahtuvat.

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
│   ├── sources/standings.py, sources/athletes.py   # pistetilanne, hiihtäjäprofiilit
│   ├── sources/results.py    # kisojen top 30 (FIS, Hiihtoliiton PDF:t)
│   ├── raceday.py            # iltapäivityksen kisapäiväportti
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
