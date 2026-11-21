# Urheilu ilmaiseksi – laajennussuunnitelma (v0.3)

*Päivitetty 2026-11-21. Tila: **U1 ja U2 toteutettu 21.11.2026** → https://henkk-code.github.io/hiihto-ylella/urheilu/ · U3 (Disney+-listat käsin) tehdään, kun Disney+ julkaisee listan. Tarkentaa [SUUNNITELMA.md](SUUNNITELMA.md):n vaihetta 3 (Laajennus).*

Muutokset v0.2 → v0.3 (toteutuksessa tarkentui):
- Viaplay TV:n maksuttomuus varmistettu: vapaa kanava 6.11.2025 alkaen, antenni- ja kaapeliverkon paikka 21.
- Katselunapit: Areena kanavakohtaisesti, MTV ja Ruutu kanavalistaan (palveluissa ei ole vakaita kanavaosoitteita), Viaplay TV:n oma sivu, Star Channelin NHL → Disney+. Warnerin kanavilta (Kutonen, TV5, TLC, Frii) nappi puuttuu.
- Vastauslaatikko: pe–su koko viikonloppu, arkisin tämä päivä ja rivi viikonlopun määrästä (viikossa noin 50 lähetystä).
- Lajipillerit omalla rivillään yläpalkissa (7 kpl), mobiilissa pelkät emojit. Kaikki-tilassa ensimmäinen klikkaus valitsee vain sen lajin, `0` palauttaa kaikki. Muut-lajin emoji 🏅.
- Kanavasuodatinta ei tehty: Disney+-välilehti hoitaa saman. Vain Disney+:ssa näkyvät ottelut ovat vain Disney+-välilehdellä, joten pääsivun "ilmaiskanavilla" pitää paikkansa.
- Studio-ohjelmat pudotetaan vain, jos ne ovat alle 60 min (pitkä "Ennakkostudio: … LIVE" on ottelu). MTV3:n "Liiga"-jatko-ohjelma yhdistetään edeltävään Hockey Night -otteluun.
- Teemavalinta on yhteinen molemmilla sivuilla.

Muutokset v0.1 → v0.2:
- §9:n kaikki viisi suositusta hyväksytty.
- Uusi §10: toteutus käytännössä, järjestys ja commitit.

## 1. Tavoite

Hiihtosivun rinnalle toinen kertasilmäyssivu, joka vastaa kysymykseen:

> **"Mitä urheilua näkyy suorana ilmaiseksi tänään ja tänä viikonloppuna, mihin aikaan ja millä kanavalla?"**

- **Ilmaiskanavat:** maksuttomat antennikanavat (Yle, MTV3, Nelonen, Sub, Jim, Kutonen, Star Channel, Viaplay TV …).
- **Ainoa poikkeus on Disney+.** Se on maksullinen suoratoistopalvelu, mutta se otetaan mukaan (NHL, ks. §4).
- Mukana vain **suorat lähetykset**. Koosteet, studiot, uusinnat ja tulosruudut jätetään pois, kuten hiihtosivulla.
- Hiihtosivu (Ylen hiihto, Kauden kisat, Maailmancup) **säilyy ennallaan**.

## 2. Mitä data jo nyt näyttää (testattu 21.11.2026)

Hiihtosivun build hakee jo nyt Telkun ryhmän **Peruskanavat** koko ohjelmiston, ja siitä käytetään vain Ylen kanavia. Ryhmän rajapintavastauksessa ovat kaikki ryhmän kanavat, joten **laajennus ei vaadi yhtään uutta hakua Telkkuun**.

Peruskanavat-ryhmä (18 kanavaa): YLE TV1 `391`, YLE TV2 `392`, MTV3 `559`, Nelonen `616`, JIM `621`, MTV Sub `560`, Liv `619`, Kutonen `393`, TLC `554`, **Star Channel `557`**, Hero `620`, Frii `555`, National Geographic `553`, Eveo `7996`, TV 5 `556`, Yle Teema Fem `570`, MTV Ava `561`, **Viaplay TV Finland `13786`**.

Viikko 21.–27.11.2026, ehto `format = SPORT` ja `broadcastType = live`: **71 ohjelmaa**.

| Kanava | Kpl | Esimerkkejä |
|---|---|---|
| Yle TV2 | 24 | hiihto, ampumahiihto, mäkihyppy, taitoluistelu, koripallon EM-karsinta |
| Viaplay TV Finland | 23 | F1 Las Vegas (harjoitukset, aika-ajot), MotoGP-luokat, alppihiihdon MC, EFL Championship, Bundesliiga, Ligue 1, Konferenssiliiga |
| MTV3 | 17 | Liiga (Hockey Night), mutta enimmäkseen *Tulosruutu* (suodatetaan pois) |
| JIM | 2 | NFL, lentopallon Mestaruusliiga |
| Kutonen | 2 | NBA, naisten jääkiekon Auroraliiga |
| Star Channel | 2 | NHL (Calgary–Chicago, New Jersey–Calgary) |
| MTV Sub | 1 | NHL (Rangers–Carolina) |

Kun studiot ja tulosruudut poistetaan, jää **noin 45–50 suoraa lähetystä viikossa**. Siitä saa luettavan listan, kun mukana on lajisuodatin.

**Havaintoja datasta** (vaikuttavat toteutukseen):
- Osa otsikoista on geneerisiä, ja joukkueet löytyvät vain kuvauksesta: `NHL 26-27` → kuvaus "NHL: Calgary Flames - Chicago Blackhawks.", `Liiga` → "Kiekko-Espoo - Jukurit, Espoo Metro Areena …". Näille tarvitaan sääntö "ottelu kuvauksen ensimmäisestä virkkeestä".
- Kuvausten päivämäärät voivat olla vanhoja (esim. "HIFK - SaiPa … (04.03.2026)"). Niitä ei käytetä, vaan aika otetaan aina kentistä `startTime` ja `endTime`.
- Star Channelilla on NHL-lähetyksen perässä `broadcastType: none` -täyteslotteja. Ne putoavat pois live-ehdolla.
- Studio-ohjelmat on merkitty `live`. Poissulkulistaan tarvitaan siis myös `Tulosruutu`, `Urheilustudio`, `Ennakkostudio`, `Jälkistudio`, `F1-Studio` sekä Hockey Night -studio-osuus, jossa ei ole ottelua.

## 3. Sivu: oma näkymä samaan repoon (suositus)

**Ehdotus:** uusi sivu `site/urheilu/index.html` osoitteeseen `…/hiihto-ylella/urheilu/`. Sivu käyttää samaa buildia, samaa Actions-ajoa ja samaa ulkoasujärjestelmää (CLAUDE.md). Hiihtosivun yläpalkkiin tulee linkki "Muu urheilu →" ja urheilusivulle vastaavasti "Hiihto Ylellä →".

Miksi ei samalle sivulle: hiihtosivun vastauslaatikko vastaa yhteen kysymykseen ("Näyttääkö Yle hiihtoa?"). Jos NHL ja F1 tulisivat samaan laatikkoon, se kysymys hämärtyisi. Kauden kisat- ja Maailmancup-välilehdet taas ovat hiihtokohtaisia.

**Hierarkia** (CLAUDE.md:n periaatteet, sovellettuna):
1. **Vastauslaatikko:** tilapilleri (🔴 LIVE nyt / ✓ Tänään N lähetystä), otsikkolause ("Tänä viikonloppuna ilmaiskanavilla 23 suoraa lähetystä") ja oikealla "Seuraava" isolla kellonajalla sekä lähtölaskennalla. Laatikon sisällä tämän päivän ja viikonlopun lähetykset.
2. **Välilehdet laskureineen:** *Tulevat lähetykset* (noin 13 vrk, päiväryhmittäin) · *Disney+* (ks. §4).
3. **Suodattimet:** lajipillerit emojeineen (🏒 Jääkiekko, ⚽ Jalkapallo, 🏎️ Moottoriurheilu, ⛷️ Talviurheilu, 🏀 Koripallo, 🏈 Amerikkalainen jalkapallo, 🏐 Muut) ja kanavavalinta *Ilmaiskanavat / Disney+ / kaikki*. Valinnat muistetaan, kuten hiihtosivulla.
4. **Rivi:** kellonaika (600), lajipilleri, sarja ("NHL", "Formula 1", "Liiga"), ottelu tai kisa, kanava sekä toissijainen nappi ("▶ Areena", "▶ Ruutu", "▶ Katsomo", "▶ Disney+"), joka avaa kanavan suoran lähetyksen.

**Lajivärit:** punainen, vihreä ja oranssi ovat jo varattuja (LIVE, kyllä, ensisijainen toiminto), ja violetti, indigo ja liukuvärit on kielletty. Talviurheilu käyttää hiihtosivun sinistä. Muille lajeille valitaan toteutuksessa erottuvat sävyt tämän rajauksen sisältä, esim. jääkiekko teräksenharmaa, jalkapallo oliivi, moottoriurheilu ruskea ja koripallo okra. Näytän ne ensin kuvakaappauksena.

## 4. Disney+ – poikkeus ilmaiskanavasääntöön

**Mitä Disney+ näyttää Suomessa kaudella 2026–27** (lähteet alla):
- **NHL:** viisivuotinen sopimus 2026–31, 160 runkosarjaottelua (näistä noin 50 Suomen iltaan sopivaan aikaan), 20 pudotuspeliottelua kahdelta ensimmäiseltä kierrokselta ja jaetut oikeudet konferenssifinaaleihin ja finaaliin. Selostus suomeksi (Vihtilä ja Pesonen). Osio "ESPN on Disney+".
- **Osa otteluista myös ilmaiseksi Star Channelilla** (esim. lokakuussa viisi ottelua, ja kaikki Monday Night Hockey -ottelut).
- Lisäksi marraskuun uutiskirjeessä mainitaan **LALIGA** ja **naisten Mestarien liiga**, mutta yksittäisiä otteluita ei listata.

**Ongelma: Disney+:n ottelulistalle ei löytynyt koneluettavaa lähdettä.** Testattu 21.11.2026:

| Vaihtoehto | Tulos |
|---|---|
| Telkku | Disney+:aa ei ole missään kanavaryhmässä (vain Star Channel ja Disney Channel). |
| NHL:n rajapinta `api-web.nhle.com` | Lähetystiedot vain USA:sta ja Kanadasta. Suomen tai Pohjoismaiden kanavia ei ole. |
| USA:n ESPN- ja ABC-ottelut Disney+:n arvauksena | Ei täsmää. Lokakuun Disney+-listan ottelut olivat USA:ssa TNT:llä tai ilman kansallista lähetystä. |
| Disney+:n ePressi-tiedotteet | Ottelulista julkaistiin vain lokakuulle (23.9.2026). Marras- ja joulukuun listoja ei ole tullut (tarkistettu tiedotteet 1.10.–20.11.). |
| disneyplus.com/fi-fi -urheilusivut | 404. Ohjelmatiedot ovat vain kirjautuneille sovelluksessa. |
| Disney+:n sisäinen rajapinta | Vaatii kirjautumistunnisteen, joten hylätty samasta syystä kuin Areenan rajapinta. |
| Fanisivut (nhlsuomi.com ym.) | Käsin koottuja ja epäluotettavia (sekoittavat Viaplayn, MTV:n ja Disney+:n). Hylätty. |

**Ehdotus, kahdessa osassa:**
- **4a – automaattinen (tehdään heti):** Star Channelin NHL-ottelut tulevat Telkusta kuten muutkin. Riville merkitään "Star Channel · myös Disney+". Tämä kattaa ilmaiseksi näkyvät Disney+-ottelut ilman käsityötä.
- **4b – vain Disney+:ssa näkyvät ottelut:** *Disney+*-välilehti, jossa on
  - käsin ylläpidetty `data/disneyplus.json` (päivä, aika, ottelu, sarja) aina, kun Disney+ julkaisee listan (nyt vain lokakuu), ja
  - pysyvä tietolaatikko: "Disney+ näyttää NHL:ää (160 ottelua), LALIGAa ja naisten Mestarien liigaa – katso ohjelma Disney+-sovelluksesta ▶".
  Jos käsin ylläpidetty lista on tyhjä tai vanhentunut, välilehdellä näkyy vain tietolaatikko ja Star Channelin ottelut. Väärää tietoa ei siis näytetä.

## 5. Lajitunnistus

Uusi asetustiedosto `config/sports.json`, samaa mallia kuin `topics.json` (regexit, ensimmäinen osuma voittaa):

| Laji | Tunnisteita (otsikko + kuvaus) |
|---|---|
| Jääkiekko | `NHL`, `Liiga`, `Mestis`, `Auroraliiga`, `jääkiekko`, `Hockey Night` + ottelu, `CHL` |
| Jalkapallo | `Bundesliiga`, `Ligue 1`, `EFL`, `Mestarien liiga`, `Konferenssiliiga`, `Veikkausliiga`, `LALIGA`, `jalkapallo`, `Huuhkajat` |
| Moottoriurheilu | `Formula 1`, `F1`, `F1 Academy`, `MotoGP`, `Moto2`, `Moto3`, `ralli`, `WRC` |
| Talviurheilu | nykyiset hiihtosäännöt + `mäkihyppy`, `alppihiihto`, `taitoluistelu`, `lumilautailu` |
| Koripallo | `NBA`, `Korisliiga`, `koripallo`, `Susijengi` |
| Amerikkalainen jalkapallo | `NFL` |
| Muut | `format = SPORT` ja live, mutta ei osumaa yllä (lentopallo, golf, yleisurheilu …). Näytetään silti, mitään ei piiloteta. |

- **Poissulku:** nykyinen `global_exclude` + `tulosruutu`, `urheilustudio`, `ennakkostudio`, `jälkistudio`, `-studio`, `sirkus`, `kaikki maalit`, `huippuhetket`.
- **Ottelun nimi:** jos otsikko on geneerinen (`NHL 26-27`, `Liiga`, `Hockey Night …`), ottelu poimitaan kuvauksen ensimmäisestä "A - B" -kuviosta.
- **Testit:** tallennetaan tämän viikon Telkku-vastaus fixtureksi ja kirjoitetaan testit yllä mainituista oikeista otsikoista (Tulosruutu pois, NHL 26-27 → Calgary Flames – Chicago Blackhawks jne.).

## 6. Arkkitehtuuri ja tietomalli

```
 Telkku (Peruskanavat, sama haku kuin nyt) ─┬─> hiihto: nykyinen suodatus → site/data.json
                                           └─> urheilu: config/sports.json → site/urheilu/data.json
 data/disneyplus.json (käsin, vaihe 4b)    ──> site/urheilu/data.json
```

```
Broadcast { id, sport, competition: "NHL", title: "Calgary Flames – Chicago Blackhawks",
            channel: "Star Channel", channel_id, also_on: ["Disney+"]?, start, end,
            live: true, watch_url, source: "telkku" | "disneyplus-manual" }
```

- `config/sources.json` → `telkku.free_channels`: kanava-id:t, nimet ja katselulinkit (Areena, Ruutu, Katsomo, Viaplay, Disney+). Kanavan lisääminen tai poistaminen on yksi rivi.
- Hallittu heikkeneminen kuten nyt: jos Telkku ei vastaa, käytetään edellistä dataa ja sivulla näkyy päivitysaika.
- Päivitys: nykyiset ajot (5.20, 15.20 ja kisapäivien 22.20) riittävät, koska TV-ohjelmisto muuttuu harvoin saman päivän aikana.
- Python-stdlib ja puhdas HTML/JS kuten nyt. Hiihtosivun ja urheilusivun yhteinen CSS siirretään omaan tiedostoonsa `site/common.css`, jotta ulkoasu pysyy yhtenäisenä.

## 7. Vaiheet ja työmäärä

| Vaihe | Sisältö | Työ |
|---|---|---|
| **U1** | Ilmaiskanavien kaikki suorat urheilulähetykset: lajitunnistus, testit, uusi sivu, linkit sivujen välillä | noin 1 pv |
| **U2 (4a)** | Star Channelin NHL "myös Disney+" -merkinnällä ja Disney+-välilehden tietolaatikko | 1–2 h |
| **U3 (4b)** | `data/disneyplus.json` käsin, aina kun Disney+ julkaisee listan | 1–2 h + käsityötä |
| myöhemmin | Suosikkijoukkueet/-sarjat (muistetaan selaimessa) ja .ics-kalenteri valituille lajeille | ei nyt |

## 8. Tunnetut aukot

- **Pelkät suoratoistot eivät ole TV-oppaissa:** Yle Areenan, Ruudun ja MTV Katsomon ilmaiset striimit (esim. osa Areenan urheilusta) puuttuvat. Sama hyväksytty rajaus kuin hiihtosivulla.
- **Disney+-ottelut puuttuvat ilman käsin päivitettävää listaa** (ks. §4).
- Peruskanavien **HD-versiot** voivat olla maksullisia joissain verkoissa. Sivulla puhutaan "maksuttomista antennikanavista".

## 9. Avoimet kysymykset (suositus ensin)

1. **Sivun paikka:** ✔ Oma sivu `/urheilu/` samassa repossa ja samalla buildilla. Vaihtoehdot: (b) kaikki samalle sivulle lajivalinnalla, (c) oma repo ja nimi (esim. `urheilu-ilmaiseksi`).
2. **Viaplay TV Finland:** ✔ Mukaan ilmaiskanavana. Se on Telkun Peruskanavat-ryhmässä, ja Viaplay itse kuvaa sen vapaaksi kanavaksi. Viikossa 23 lähetystä (F1, MotoGP, alppihiihto, jalkapallo), joten se on listan toiseksi suurin. Maksuttomuus tarkistetaan vielä Digitan antenniverkon kanavalistasta ennen toteutusta.
3. **Disney+-vain-ottelut:** ✔ 4a heti ja 4b vain silloin, kun Disney+ julkaisee listan. Muuten pelkkä tietolaatikko ja linkki. Vaihtoehto: Disney+-ottelut jätetään kokonaan pois, ja vain Star Channel näytetään.
4. **"Muut"-laji:** ✔ Näytetään kaikki suorat urheilulähetykset, myös tunnistamattomat, "Muut"-pillerillä. Vaihtoehto: vain tunnistetut lajit.
5. **Talviurheilu urheilusivulla:** ✔ Mukana (mäkihyppy, alppi, taitoluistelu, hiihto), ja rivillä linkki hiihtosivulle hiihtolajeissa. Vaihtoehto: hiihtolajit vain hiihtosivulla.

Päätökset 21.11.2026: kaikki viisi suositusta hyväksyttiin.

## 10. Toteutus käytännössä

**Periaate:** jokainen push mainiin julkaisee sivun Actionsin kautta, ja Actions ajaa testit ennen buildia. Kaatuva testi estää siis julkaisun. Siksi edetään pienin, itsenäisesti julkaistavin commitein. Mikään vaihe ei riko hiihtosivua, ja urheilusivu tulee näkyviin vasta, kun se on valmis (commit 4).

**Ennen jokaista pushia, paikallisesti:**
1. `python3 -m unittest discover -s build/tests` vihreänä
2. `python3 build/build.py` oikealla datalla, ja tulosteesta tarkistetaan lähetysmäärät
3. `cd site && python3 -m http.server 8000` ja kuvakaappaukset: vaalea ja tumma teema sekä mobiilileveys 390 px. Hiihtosivu tarkistetaan joka kerta, ettei siihen tullut muutoksia.

**Ennen commitia 3:** tarkistetaan Viaplay TV Finlandin maksuttomuus Digitan antenniverkon kanavalistasta. Jos kanava ei ole maksuton, se jätetään pois `free_channels`-listalta (yksi rivi).

### Commitit

| # | Commit | Sisältö | Näkyy käyttäjälle |
|---|---|---|---|
| 1 | **Suunnitelma: urheilulaajennus v0.2 hyväksytty** | tämä tiedosto ja linkki SUUNNITELMA.md:ssä | ei (vain dokumentti) |
| 2 | **Yhteinen tyylitiedosto hiihto- ja urheilusivulle** | Hiihtosivun `<style>`-lohkosta yleiset osat (teematokenit, laatikot, pillerit, napit, välilehdet, typografia) tiedostoon `site/common.css`. Hiihtokohtaiset tyylit (lajivärit, tulos- ja profiilinäkymät) jäävät sivulle. Puhdas refaktorointi. | ei. Hiihtosivu näyttää täsmälleen samalta (kuvakaappaukset ennen ja jälkeen). |
| 3 | **Urheilulähetysten tunnistus ja urheilu/data.json** | `config/sports.json` (lajit, sarjat, poissulut, geneeriset otsikot) · `config/sources.json` → `telkku.free_channels` (kanavat ja katselulinkit) · `build/sports.py`: lajin ja sarjan tunnistus sekä ottelun poiminta kuvauksesta · build.py: sama Telkku-haku palvelee molempia sivuja (Ylen kanavat → hiihto, ilmaiskanavat → urheilu), tulos tiedostoon `site/urheilu/data.json` · edellisen julkaisun data varalle, jos Telkku ei vastaa · fixture `telkku_peruskanavat_2026-11-21.json` (viikko) ja testit oikeilla otsikoilla · DATALAHTEET.md: §4 ilmaiskanavat ja uusi §7 Disney+ (testatut vaihtoehdot) | ei. `urheilu/data.json` julkaistaan, mutta sivua ei vielä ole. Ensimmäiset ajastetut ajot näyttävät oikean datan ennen sivun avaamista. |
| 4 | **Urheilu ilmaiseksi -sivu** | `site/urheilu/index.html`: vastauslaatikko (LIVE nyt / seuraava ja lähtölaskenta), Tulevat lähetykset päiväryhmittäin, laji- ja kanavasuodattimet, teemanappi, pikanäppäimet ja `?`-ohje, URL-hash, valintojen muistaminen (`urheilu:`-etuliite) · linkit "Muu urheilu →" ja "Hiihto Ylellä →" sivujen yläpalkkeihin · README: uusi sivu ja ylläpito | **kyllä, sivu tulee liveksi.** Ennen pushia näytän sinulle kuvakaappaukset lajiväreistä ja sivusta, ja pushaan vasta hyväksynnän jälkeen. |
| 5 | **Disney+: Star Channelin NHL ja Disney+-välilehti** | Star Channelin riveille "myös Disney+" ja ▶ Disney+ -nappi · Disney+-välilehti laskurilla: tietolaatikko (NHL, LALIGA, naisten Mestarien liiga ja linkki) ja Star Channelin ottelut · `data/disneyplus.json` (aluksi tyhjä lista) ja sen luku buildissa, jolloin myöhemmät listat ovat pelkkiä datacommiteja · SUUNNITELMA-URHEILU.md: tila toteutettu | kyllä |

**Yhteensä 5 committia.** Sivu on livenä commitissa 4 ja täysin valmis (U1 + U2) commitissa 5. Arvioitu työ on noin 1,5 päivää, josta commit 3 on suurin (noin puoli päivää).

**Myöhemmin (U3, ei omaa kehityscommitia):** kun Disney+ julkaisee kuukauden NHL-listan, rivit lisätään tiedostoon `data/disneyplus.json` (commit "Disney+:n NHL-ottelut joulukuu 2026"). Build hylkää menneet ottelut itse, ja vanhentunut lista ei näy.

### Toteutuksen yksityiskohtia

- **`build/sports.py`:** `SportClassifier.classify(title, description) → {sport, competition} | None`. Toisin kuin hiihdon luokittelija, tämä katsoo myös kuvausta, mutta vain kun otsikko on geneerinen (`NHL 26-27`, `Liiga`, `Hockey Night …`). Ottelun nimi tulee kuvauksen ensimmäisestä "Joukkue A - Joukkue B" -kuviosta, ja kuvauksen päivämäärät ohitetaan.
- **Telkku-haku:** `telkku.fetch_programs` saa kanavalistaksi Ylen kanavien ja ilmaiskanavien unionin. Hakuja ei tule lisää, koska vastauksessa on jo koko ryhmä. Hiihtopuolen suodatus pysyy ennallaan, ja sen nykyiset testit varmistavat sen.
- **Tila:** `urheilu/data.json`:ssa on oma `status.telkku` (ok tai vanha data, päivitysaika), ja sivun alalaidassa näkyy päivitysaika, datan tila ja lähteet.
- **Actions:** ei muutoksia. Nykyiset ajot (5.20, 15.20 ja kisapäivien 22.20) ja pushit riittävät.
- **Peruutus:** jokainen commit on yksittäin peruttavissa (`git revert`). Commit 4 on ainoa, joka tuo uuden sivun näkyviin.

## Lähteet

- NHL ja Disney+ -sopimus: https://www.nhl.com/fi/news/nhl-ja-disney-julkistivat-sopimuksensa
- Disney+:n NHL-aikataulu, lokakuu 2026 (ePressi 23.9.2026): https://www.epressi.com/tiedotteet/elokuvat-ja-televisio/disney-julkistaa-nhl-otteluiden-lahetysaikataulun-suomessa.html
- Disney+:n marraskuun 2026 uutiskirje (LALIGA, naisten Mestarien liiga): https://www.epressi.com/tiedotteet/elokuvat-ja-televisio/disney-palvelun-marraskuun-2026-sisaltouutiskirje.html
- Star Channelin NHL-ottelut: https://mesta.net/huippu-uutinen-nhl-otteluita-myos-star-channel-tv-kanavalla/
- Viaplay TV vapaana kanavana: https://www.nhl.com/fi/news/viaplay-avasi-uuden-vapaan-urheilukanavan
- Telkku-rajapinta: ks. [DATALAHTEET.md §4](DATALAHTEET.md)
