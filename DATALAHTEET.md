# Datalähteet (v0.4)

*Päivitetty 2026-11-21.*

## 1. Ylen kausilista – PÄÄLÄHDE (tapahtumataso)

Lähde: https://yle.fi/a/74-20251336 (julkaistu 14.10.2026). Ylläpidetään käsin tiedostossa `data/events.json`.
Lyhenteet: SC = Suomen cup, MC = maailmancup, SM = Suomen mestaruuskisat, MM = maailmanmestaruuskisat.

### Hiihto 2026–27
| Päivät | Paikka | Tyyppi |
|---|---|---|
| 31.10.–1.11.2026 | Vuokatti | SC |
| 21.–22.11.2026 | Ruka | SC |
| 27.–29.11.2026 | Ruka | MC |
| 4.–6.12.2026 | Trondheim | MC |
| 16.–17.1.2027 | Vantaa | SC |
| 29.–31.1.2027 | Toblach | MC |
| 5.–7.2.2027 | Iisalmi | SM |
| 12.–14.2.2027 | Lahti | MC |
| 25.2.–7.3.2027 | Falun | MM |
| 19.–21.3.2027 | Ulricehamn | MC |
| 3.–4.4.2027 | Taivalkoski | SC |
| 9.–11.4.2027 | Rovaniemi | SM |

### Ampumahiihto 2026–27
| Päivät | Paikka | Tyyppi |
|---|---|---|
| 26.–29.11.2026 | Kontiolahti | MC |
| 4.–6.12.2026 | Hochfilzen | MC |
| 10.–13.12.2026 | Annecy – Le Grand-Bornand | MC |
| 2.–3.1.2027 | Pokljuka | MC |
| 6.–10.1.2027 | Ruhpolding | MC |
| 14.–17.1.2027 | Antholz-Anterselva | MC |
| 21.–24.1.2027 | Nové Město na Moravě | MC |
| 10.–21.2.2027 | Otepää | MM |
| 4.–7.3.2027 | Oberhof | MC |
| 11.–14.3.2027 | Östersund | MC |
| 18.–21.3.2027 | Oslo | MC |

## 2. FIS iCal-syöte – kisataso (testattu 2026-11-20)

Virallinen, tilattavaksi tarkoitettu syöte (FIS-kalenterin "Subscribe to Calendar" -painike):

```
https://www.fis-ski.com/DB/services/public/icalendar-feed-fis-events.html?seasoncode=2027&sectorcode={CC|JP|NK}&categorycode={WC|WSC|FIS}[&nationcode=FIN]
```

| Syöte | Tapahtumia | Huom. |
|---|---|---|
| CC + WSC (Falun MM, maastohiihto) | 18 | kisat 24.2.–7.3.2027 |
| JP + WSC (Falun MM, mäkihyppy) | 11 | ei mukaan |
| NK + WSC (Falun MM, yhdistetty) | 7 | mukaan (Gundersen, joukkue, sprintti) |
| CC + WC (maailmancup) | 85 | koko kausi, kaikki paikat |
| CC + FIS + FIN (FIS-kisat Suomessa) | 46 | Suomen cupin kisat todennäköisesti tässä, liitos paikka+päivä tarkistetaan |

- Jokainen kisa on oma VEVENTinsä: `SUMMARY` (paikka, kategoria, matka, tyyli), `DESCRIPTION` (sukupuoli, tulos-/lähtölistalinkki), `UID` (= FIS race id).
- ➖ **Vain päivämäärä** (`DTSTART;VALUE=DATE`), ei lähtöaikaa
- ➖ Ei CORS-otsakkeita → haetaan build-vaiheessa, ei selaimessa
- Huom: FIS-syötteen mukaan Falunin kisat alkavat jo 24.2. (Ylen lista: 25.2.). Kisapäivät näytetään FIS:n mukaan.

## 3. Ampumahiihto – kisataso (avoin)
- IBU:n tulospalvelun rajapinta (`api.biathlonresults.com`) palauttaa nyt HTTP 401, eli vaatii tunnistautumisen. Ei käytetä.
- Selvitetään vaiheessa 2: biathlonworld.com-kalenterin mahdollinen iCal, tai kisaohjelma käsin `events.json`iin (~10 kisaa/tapahtuma).

## 4. Lähetysajat – Telkku.comin rajapinta (VALITTU, testattu 2026-11-20)

Telkku.com (Iltalehti) hakee TV-oppaansa avoimesta JSON-rajapinnasta. Sama lähde on iptv-org/epg-projektin `iltalehti.fi`-hakijassa.

```
GET https://il-telkku-api.prod.il.fi/v1/channel-groups                      # kanavaryhmät ja kanava-id:t
GET https://il-telkku-api.prod.il.fi/v1/channel-groups/{ryhmä}/offering?startTime={ISO}&endTime={ISO}
```

- Ei API-avainta. `Access-Control-Allow-Origin: *`. Rajapinnan juuressa ei ole robots-rajoituksia.
  (Huom: iltalehti.fi:n robots.txt kieltää AI-indeksoijat. Meidän skriptimme ei indeksoi, vaan hakee kerran vuorokaudessa.)
- Ryhmä **Peruskanavat** `d63736b5-7f72-45d4-8f9e-6505f1bac855`: YLE TV1 = `391`, YLE TV2 = `392`, MTV3 = `559`, Nelonen = `616`, MTV Sub = `560` …
  (Yle Teema Fem tarkistetaan toteutuksessa, kandidaatit `570`/`7996`/`13786`.)
- Ohjelman kentät: `programName, description, startTime, endTime (UTC), broadcastType (live|rerun|none), format (SPORT|EPISODIC|MOVIE|SINGLE), programId, slug, images …`
- **Ulottuvuus ~13 vrk** (20.11. haettuna data loppui 3.12. aikana)
- Testitulos, Yle TV2 la 28.11.2026 (ajat Suomen aikaa), kaikki `live`:
  - 09.40 Maastohiihto: Sprinttikarsinnat (p) Ruka
  - 11.10 Yhdistetyn maailmancup: M HS 142 Ruka *(mäkiosuus, suodatetaan pois)*
  - 12.10 Maastohiihto: Sprinttifinaalit (p) Ruka
  - 14.05 Ampumahiihdon maailmancup: Pariviesti, Kontiolahti
  - 15.25 Yhdistetyn maailmancup: M 10 km Ruka *(hiihto-osuus, mukaan)*
  - 16.10 Ampumahiihdon maailmancup: Sekaviesti, Kontiolahti
  - 17.25 Mäkihypyn maailmancup: HS 142, Ruka *(pois)*
- ➖ Epävirallinen. Ei Areena-only-lähetyksiä.

## 5. Maailmancupin pistetilanne (ehdotus, testattu 2026-11-21)

**Hiihto ja yhdistetty – FIS cup standings (HTML):**
```
https://www.fis-ski.com/DB/{cross-country|nordic-combined}/cup-standings.html?sectorcode={CC|NK}&seasoncode=2027&cupcode=WC&disciplinecode=ALL&gendercode={M|W}&nationcode=
```
- Kausi 2026 jäsentyy: "After Men's 20km Mass Start Free Lake Placid (USA) 22-03-2026 (42/42)", jonka jälkeen rivit nimi, maa, pisteet (kokonais, matka, sprintti).
- ⚠️ **Ansa:** ennen kauden ensimmäistä MC-kisaa (2027) sivu näyttää hiljaa toisen cupin (Australia New Zealand Cup). Jäsentimen on tarkistettava, että valittuna on `WC`, ja muuten jätettävä data tyhjäksi.
- Ei CORS-otsakkeita, joten haetaan buildissa. Neljä sivulatausta vuorokaudessa.

**Ampumahiihto:** `api.biathlonresults.com` palauttaa 401 (vain `Seasons` on auki), joten sitä ei käytetä.
Ehdotus: en.wikipedia "2026–27 Biathlon World Cup" (MediaWiki API `action=parse`). Sivu on olemassa ja siinä on Standings → Overall (M/N). Vapaaehtoisten ylläpitämä ja yleensä ajan tasalla kisapäivän iltana.

**Profiilit (arvio, ei toteuteta):** Wikidata `P2773` = FIS competitorid (4 001 hiihtäjää), Wikipedia REST `page/summary` (ingressi ja kuva, CC BY-SA), FIS athlete-biography-sivu (HTML). Ks. SUUNNITELMA.md.

## 6. Hylätyt / varalla
- **Areenan TV-opasrajapinta** (`areena.api.yle.fi/v1/ui/schedules/…`): ilman Ylen web-sovelluksen tunnisteita HTTP 403. Tunnisteiden käyttö julkisella sivulla ei ole asiallista. Hylätty.
- **Ylen Teksti-TV API** (developer.yle.fi): virallinen, vaatii ilmaisen avaimen Yle Tunnuksella. Data on tekstisivuja. Varalähde, jos Telkku lakkaa toimimasta.
- **DVB-T EPG omasta antennista**: virallinen ja kattava, mutta vaatii laitteiston. Ei tarvetta nyt.
