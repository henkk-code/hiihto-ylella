# CLAUDE.md

## UI & UX Design Rules
Sivu on kertasilmäyssivu: "Näyttääkö Yle hiihtoa tänä viikonloppuna, milloin ja millä kanavalla?" Ulkoasu lainaa GitHubin (Primer) rakenteen ja PostHogin lämmön ja leikkisyyden.

Kokeiltu ja hylätty – älä palaa näihin:
- Tiheä Carbon-dashboard (sivupalkki, tunnuslukulaatikot, taulukot): liian työkalumainen.
- Minimalistinen yksi sarake ilman värejä ja laatikoita: tylsä, ei hierarkiaa, vaikea seurata.
- Geneerinen "Claude-tyyli" (pehmeät varjokortit, sinivioletti).

### Hierarkia (tärkein ensin)
1. **Vastauslaatikko** ylimpänä: tilapilleri (✓ Kyllä / Ei lähetyksiä), otsikkolause ja oikealla "Seuraava lähetys" isolla kellonajalla ja lähtölaskennalla ("alkaa 3 h 20 min päästä"). Saman laatikon sisällä viikonlopun lähetykset.
2. **Välilehdet laskureineen** (GitHub UnderlineNav): Tulevat lähetykset · Kauden kisat. Valittu välilehti näkyy URL-hashissa.
3. Alalaita: päivitysaika, datan tila, lähteet.

### Rakenne (GitHub)
- Yksi keskitetty sarake (max n. 920px) lämpimällä taustalla (PostHog-beige); sisältö GitHubin Box-tyylisissä laatikoissa: 1px reuna, 6px pyöristys, otsikkorivi vaaleammalla pohjalla, rivien välissä ohut viiva. Yksi laatikko per looginen lista, ei laatikoita laatikoissa, ei varjoja.
- Päiväryhmät laatikon sisäisinä ryhmäotsikoina ("Lauantai 21.11." + "huomenna").
- Suhteelliset ajat aina absoluuttisen rinnalla: "huomenna", "6 pv päästä", "alkaa 45 min päästä".

### Typografia
- IBM Plex Sans kaikkialla, tabular-nums kellonajoille ja päivämäärille (ei monospacea leipätekstissä).
- Painot kantavat hierarkiaa: kellonajat ja ohjelmien nimet 600, otsikot 700, metatieto 13px himmeänä.

### Värit (semanttiset, ei koristeellisia)
- Pohja lämmin neutraali (vaalea #F2F2EE / laatikot #FFFFFF; tumma #151513 / laatikot #1C1C1A).
- **Lajivärit** johdonmukaisesti suodattimissa, lajipillereissä ja rivin vasemmassa reunaviivassa: Hiihto sininen, Ampumahiihto keltaruskea, Yhdistetty turkoosi.
- Vihreä = kyllä / käynnissä, punainen = LIVE nyt, poltettu oranssi #D9480F = ensisijainen toiminto, valittu välilehti ja fokus.
- Ei violettia, indigoa eikä liukuvärejä.

### Komponentit
- Pillerit (täysin pyöreät) lajeille, tiloille ja laskureille; laatikot ja napit 6px pyöristys.
- Ensisijainen nappi PostHog-tyyliin: oranssi, tummempi 3px alareuna (painuu klikatessa). Toissijaiset napit GitHub-tyyliin: pieni, reunallinen ("▶ TV2" avaa Areenan).
- Lajiemojit suodattimissa ja lajipillereissä (🎿 🎯 ⛷️); pienet viivaikonit metatiedossa. Ei koristekuvituksia.

### Teema ja näppäimistö
- Vaalea ja tumma teema, teemanappi yläpalkissa, valinta muistetaan, oletus seuraa laitetta.
- Pikanäppäimet (ohje `?`-näppäimen takana), ei näkyvää näppäinohjetta pääsivulla.
