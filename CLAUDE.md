# CLAUDE.md

## UI & UX Design Rules (Strict)
Sivu on kertasilmäyssivu (yksi kysymys, kymmeniä rivejä), ei työkalu tai dashboard. Rauhallinen ja selkeä menee tiheyden edelle.

- Design System: Carbon / Primer -henkinen utilitaarisuus: selkeys, ei koristeita, ei "Claude-geneeristä" ilmettä. Ei Material Designia.
- Layout & Structure: Yksi keskitetty sarake (max n. 840px), ei sivupalkkia. Ei "card soupia" eikä varjostettuja kortteja. Rakenne syntyy väljästä pystyrytmistä, väliotsikoista ja harkituista 1px hiusviivoista – ei viivaa jokaisen rivin väliin eikä harmaita palkkeja.
- Typography: IBM Plex Sans käyttöliittymätekstille, IBM Plex Mono + tabular-nums kellonajoille, päivämäärille ja luvuille. Pääkysymyksen vastaus näytetään isolla yhtenä lauseena, ei tunnuslukulaatikoina.
- Color Palette: Ei violettia, indigoa tai sini-violetti-liukuvärejä. Lämmin neutraali pohja (#FAFAF9 vaalea / #141312 tumma) ja yksi toiminnallinen korostusväri (#D9480F poltettu oranssi) vain ensisijaisille toiminnoille ja aktiivisille tiloille. Toistuvaa metatietoa (laji, sarja) näytetään himmeänä tekstinä, ei värikoodeina eikä tageina joka rivillä.
- Theming: Vaalea ja tumma teema; teemanappi yläpalkissa, valinta muistetaan, oletus seuraa laitetta.
- Geometry & Depth: Border-radius enintään 2px. Ei varjoja; syvyys pinnan sävyeroilla ja 1px reunoilla.
- Navigation & UX: Näppäimistöllä käytettävä (oikotiet, ohje `?`-näppäimen takana), mutta ei näkyvää näppäinohjetta tai navigaatiopalkkia pääsivulla. Ei markkinointityylisiä hero-osioita.
