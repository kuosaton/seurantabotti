# Seurantabotti, vaatimusmäärittely

## Tarkoitus

Seurantabotti on automaattinen seurantatyökalu, joka auttaa Kuluttajaliittoa varautumaan ajoissa eduskunnan valiokunnissa käsiteltäviin asioihin sekä lausuntopalvelu.fi:n lausuntopyyntöihin.

Tällä hetkellä kuulemiskutsut tulevat Kuluttajaliitolle usein lyhyellä varoitusajalla. Botin tehtävä on antaa lisää varautumisaikaa ennen virallisia kutsuja, jotta lausuntoihin voi valmistautua rauhassa.

Keskeinen periaate on, että botti ei korvaa Kuluttajaliiton virallisia kutsuja, vaan täydentää niitä. Ei ole katastrofaalista, jos botti ei nosta jotakin, sillä kutsut tulevat Kuluttajaliitolle joka tapauksessa. Sen sijaan turhat nostot heikentäisivät työkalun hyötyä, sillä sen tarkoitus on vähentää tiedon paljoutta, ei lisätä sitä.

## Käyttäjän ongelma

Valiokuntien nettisivuja seurataan tällä hetkellä manuaalisesti. Ongelma on tiedon paljous: päivityksiä ja uusia asioita tulee runsaasti, ja on työlästä selvittää yksitellen, mitkä voisivat olla Kuluttajaliitolle relevantteja.

Seurantabotin tavoite on vähentää manuaalista työtä karsimalla pois asiat, jotka eivät koske Kuluttajaliittoa; antaa varoaikaa nostamalla relevantit asiat esiin ennen virallisia kutsuja; ja perustella nostot lyhyesti, jotta käyttäjä voi nopeasti arvioida, kannattaako asiaan tutustua tarkemmin.

## Seurattavat lähteet

### 1. Eduskunnan valiokunnat

Seurattavat valiokunnat ovat talousvaliokunta, maa- ja metsätalousvaliokunta sekä ympäristövaliokunta. Näistä talousvaliokunta on Kuluttajaliitolle tärkein. Muiden valiokuntien osalta Kuluttajaliitto saa kutsut omia kanaviaan pitkin, joten niitä ei seurata aktiivisesti.

### 2. Lausuntopalvelu.fi

Kaikki uudet lausuntopyynnöt arvioidaan relevanssin näkökulmasta riippumatta lausunnon pyytäjästä.

### 3. Kuluttajaliiton verkkosivut (tausta-aineisto)

Botti tutustuu automaattisesti Kuluttajaliiton verkkosivujen sisältöön, erityisesti julkaistuihin lausuntoihin ja kannanottoihin, ja päättelee niiden perusteella, mitkä aihepiirit ovat Kuluttajaliitolle relevantteja. Staattista avainsanalistaa ei ylläpidetä manuaalisesti.

## Toimintalogiikka

### Valiokunta-aikataulut

Tärkein tarkistusajankohta on perjantai. Perjantaisin julkaistaan yleensä seuraavan viikon aikataulupäivitykset, joten viikkokatsaus lähetetään perjantaina. Muina arkipäivinä tehdään kevyempi tarkistus mahdollisten päivitysten varalta. Mahdolliset muutokset välitetään, mutta kynnys on korkeampi.

### Lausuntopalvelu

Lausuntopalvelua tarkistetaan päivittäin. Uudet lausuntopyynnöt havaitaan yleensä vuorokauden sisällä julkaisusta. Aikataulupaine on pienempi kuin valiokuntien osalta, sillä lausuntopyynnöillä on tyypillisesti pidempi vastausaika.

### Relevanssiarviointi

Jokainen asia arvioidaan yksilöllisesti. Arviointi perustuu ensinnäkin asian otsikkoon, kuvaukseen ja liitteiden sisältöön, ja toiseksi Kuluttajaliiton verkkosivujen ajantasaiseen sisältöön, eli painopisteisiin ja viimeaikaisiin lausuntoihin.

Botti antaa jokaiselle arvioidulle asialle relevanssipisteen asteikolla 0–10 sekä lyhyen perustelun suomeksi. Esimerkki perustelusta:

> _"Koskee suoraan verkkokaupan kuluttajansuojaa. Kuluttajaliitto on antanut aiheesta kaksi lausuntoa viimeisen vuoden aikana."_

### Kynnysarvot

| Pistemäärä | Toimenpide                                   |
| ---------- | -------------------------------------------- |
| 7–10       | Nostetaan sähköpostikatsaukseen              |
| 4–6        | Tallennetaan lokiin, ei lähetetä sähköpostia |
| 0–3        | Ohitetaan                                    |

Suunnitteluperiaatteena on mieluummin tarkempi kuin laajempi nostokynnys. Jos jokin asia jää nostamatta, ei ole kriittistä, sillä Kuluttajaliitto saa tästä joka tapauksessa kutsun. Sen sijaan turhat nostot vähentäisivät työkalun hyödyllisyyttä, sillä sen tarkoitus on juuri vähentää tiedon paljoutta.

Kynnysarvoa voidaan kalibroida käytön myötä palautteen perusteella. Lokiin tallennettuja "melkein nostettuja" asioita voidaan myöhemmin tarkastella, jotta nähdään, jäikö jotain oikeasti tärkeää nostamatta.

## Tulosteet

### Viikkokatsaus (perjantaisin)

Sähköposti, joka sisältää talousvaliokunnan, maa- ja metsätalousvaliokunnan sekä ympäristövaliokunnan tulevan viikon ohjelmasta nostetut asiat. Kunkin noston yhteydessä näytetään otsikko, käsittelypäivämäärä, relevanssipistemäärä, perustelu sekä linkki alkuperäiseen aineistoon.

Jos viikolla ei ole yhtään nostettavaa asiaa, sähköpostissa kerrotaan tämä lyhyesti. Tällainen "hiljainen viikko" -viesti antaa myös tiedon siitä, että botti toimii.

### Päivittäinen lausuntopalvelukatsaus

Sähköposti, joka lähetetään vain kun uusia relevantteja lausuntopyyntöjä on ilmestynyt. Tyhjiä viestejä ei lähetetä.

Sisältö on samaa muotoa kuin viikkokatsauksessa: otsikko, lausunnon pyytäjä, määräaika, relevanssipistemäärä ja perustelu, sekä linkki lausuntopalveluun.

### Toimitustapa

Ensisijainen toimitustapa on sähköposti. Mahdollinen myöhempi laajennus on web-käyttöliittymä, josta nostettuja asioita ja historia näkee selaimessa. Tätä arvioidaan myöhemmin.

## Mitä botti ei tee

Rajataan selkeästi, ettei odotusten ja toteutuksen välille synny kuilua.

- Botti ei korvaa virallisia kuulemiskutsuja. Ne tulevat Kuluttajaliitolle joka tapauksessa.
- Botti ei tee lopullista arviota siitä, pitääkö asiaan reagoida. Sen tehtävä on nostaa esiin todennäköisiä kandidaatteja. Asiantuntija tekee lopullisen arvion.
- Botti ei kirjoita lausuntoja tai vastauksia. Kyse on pelkästään seurannasta ja tiivistämisestä.
- Botti ei seuraa muita valiokuntia kuin talous-, maa- ja metsätalous- sekä ympäristövaliokuntaa.
- Botti ei takaa 100 %:n kattavuutta. Tarkoituksella pidetään korkea relevanssikynnys, jolloin osa asioista jää nostamatta.

## Onnistumisen mittarit

Työkalu on onnistunut, jos Kuluttajaliitto saa tiedon relevantista valiokunta-asiasta ennen virallista kutsua merkittävässä osassa tapauksista, jos sähköpostikatsaukset ovat lyhyitä ja osuvia niin että käyttäjän ei tarvitse seuloa nostoja, ja jos käyttäjä ei palaa manuaaliseen seurantaan vaan luottaa botin nostoihin.

Epäonnistumisen merkkejä ovat tilanteet, joissa käyttäjä alkaa ohittaa sähköposteja koska niissä on liikaa irrelevanttia, käyttäjä tarkistaa asioita silti manuaalisesti varmuuden vuoksi, tai nostot ovat oikeita mutta perustelut niin ylimalkaisia, ettei niistä saa käsitystä siitä, kannattaako asiaan tutustua.

## Kehitysvaiheet lyhyesti

V1, perusprototyyppi: päivittäinen lausuntopalveluseuranta, sähköpostitoimitus, LLM-pohjainen relevanssiarviointi Kuluttajaliiton verkkosivujen pohjalta.

V2, valiokuntaseuranta: talous-, maa- ja metsätalous- sekä ympäristövaliokunnan viikko-ohjelmien seuranta, perjantaikatsaukset.

V3, hienosäätö: liitetiedostojen (PDF, DOCX) sisällön hyödyntäminen arvioinnissa, palautepohjainen kynnyksen kalibrointi.

Mahdolliset myöhemmät laajennukset: web-käyttöliittymä historian selaamiseen, useamman valiokunnan seuranta tarpeen mukaan, useamman käyttäjän tuki (esim. koko tiimi).

---

Dokumentti päivitetty 22.4.2026. Versio 1.1.
