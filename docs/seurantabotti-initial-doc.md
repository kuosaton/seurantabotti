# Seurantabotti initial doc

## Asiakas kysyi

_Kuinka vaikeaa olisi luoda oma botti tmv joka seuraisi eduskunnan valiokuntien nettisivuja ja antaisi mulle jonkun viikkokatsauksen tiivistettynä?_

- _Sen pitäisi lukea nettisivuja ja avata liitetiedostoja, joissa on lisätietoa._

- _Ideaalitilanteessa se osaisi myös arvioida Kuluttajaliiton nettisivuilla julkaistujen lausuntojen perusteella, onko valiokunnassa tulossa oleva asia meille relevantti eli osaisi tehdä nostoja._

- _Samaa toiminnallisuutta kaipaisin myös lausuntopalvelu.fi-palvelun seuraamiseen, mutta reaaliaikaisemmin (valiokunnat yleensä julkaisee viikkosuunnitelmia, kun taas lausuntopalveluun voi päivittäin pamahtaa jotain tärkeää)._

## Tarkentavat kysymykset asiakkaalle

**Q1**. Onko tiettyjä valiokuntia, jotka ovat Kuluttajaliitolle relevantimpia kuin toiset?

- **A1**. _Talousvaliokunta, Maa- ja metsätalousvaliokunta ja Ympäristövaliokunta. Näistä kolmesta Talousvaliokunta on Kuluttajaliitolle tärkein._

**Q2**. Kun lausuntopalveluun ilmestyy jotain relevanttia, kuinka nopeasti Kuluttajaliiton pitää reagoida, päiviä, viikko, enemmän? Onko ollut tapauksia, joissa jokin tärkeä asia on jäänyt huomaamatta tai tullut vastaan liian myöhään?

- **A2**. _Ei varsinaisesti, sillä Kuluttajaliitto saa joka tapauksessa kutsun kuulemisiin. Työkalun tarkoitus: tällä hetkellä kutsut kuulemisiin tulee viime tingassa, ja tällaisella työkalulla niihin voisi saada lisää varautumisaikaa. Perjantaisin tulee yleensä päivitykset aikatauluihin. viikottain siis kriittisimmät, viikolla tulee myös päivityksiä mutta ovat vähemmän kriittisiä._

**Q3**. Missä muodossa tiivistelmä olisi hyödyllisin, Telegram-viesti, sähköposti, vai jokin muu?

- **A3**. _Sähköposti olisi hyödyllisin._ (Dev näkemys: Jos tiivistelmän näkisi web-sivulta, sekin voisi toimia. Tätä voisi pohtia myöhemmin.)

**Q4**. Riittääkö pelkkä “hei, tämä kannattaa katsoa” -tason nosto, vai pitäisikö botin tuottaa myös lyhyt analyysi siitä, miksi asia on Kuluttajaliitolle relevantti?

- **A4**. _Olisi hyvä saada lyhyt perustelu sille, miksi asia on Kuluttajaliitolle relevantti._

**Q5**. Onko tiettyjä aihepiirejä, jotka ovat aina relevantteja (esim. Kuluttajansuoja, tuoteturvallisuus, digipalvelut), ja sellaisia jotka eivät ole koskaan?

- **A5**. _Tästä on vaikea sanoa. Oikeastaan parhaiten toimisi, jos botti voisi tutustua Kuluttajaliittojen sivujen sisältöön ja tämän perusteella päätellä, olisiko aihe relevantti._

**Q6**. Miten seuraatte tällä hetkellä valiokuntien toimintaa sekä lausuntopalvelua, manuaalisesti, RSS, sähköposti-ilmoitukset? Mikä nykyisessä tavassa ei toimi?

- **A6**. _Manuaalisesti valiokuntien nettisivuilta. Nykyisessä tavassa ongelmana on tiedon paljous: päivityksiä tulee vino pino, ja on työlästä selvittää, mitkä voisivat olla Kuluttajaliitolle relevantteja._

**Q7**. Kuinka paljon “turhia” nostoja siedät: onko parempi saada mahdollisesti liikaa ehdotuksia (joista osa ohi) vai vain varmat osumat (mutta riski että jotain jää pois)?

- **A7**. _Mielummin tarkempi. jos jotain menee ohi, ei ole niin kriittistä, sillä Kuluttajaliitto saa joka tapauksessa kutsun. Väärät hälytykset sen sijaan saattavat vähentää työkalun hyödyllisyyttä, sillä sen on tarkoitus vähentää tiedon paljoutta._

## Kontekstia

### [Kuluttajaliitto ry](https://www.kuluttajaliitto.fi/)

Kuluttajaliitto on itsenäinen, poliittisesti sitoutumaton ja riippumaton suomalainen yhdistys, joka ajaa kuluttajan etuja ja oikeuksia.

Kuluttajaliiton tarkoituksena on koota kuluttaja-asemastaan kiinnostuneet ihmiset toimimaan etujensa puolesta sekä edistää kuluttajatietoisuutta ja tiedostavaa kuluttajuutta. Liitto valvoo vapaan kansalaistoiminnan keinoin kuluttajien etuja yhteiskunnassa ja markkinoilla. Liitto edistää oikeudenmukaisuuden ja kohtuuden periaatteita kulutuksessa sekä toimii ympäristön suojelemiseksi kuluttajapolitiikan keinoin.

Kuluttajaliitto edustaa laajasti kuluttajia valtionhallinnon ja yhteistyökumppaneiden neuvottelukunnissa, työryhmissä ja hankkeissa. Järjestö tekee aloitteita, antaa lausuntoja ja osallistuu kuluttajien etuihin ja oikeuksiin vaikuttavaan päätöksentekoon myös yhteiskunnallisen keskustelun kautta. Liitto tukee kuluttajien vapaata kansalaistoimintaa paikallisella, alueellisella ja valtakunnallisella tasolla. Liitolla on paikallisten, alueellisten ja valtakunnallisten kuluttajayhdistysten lisäksi laaja valtakunnallisista järjestöistä muodostuva jäsen- ja yhteistyöverkosto ([Wikipedia (fi): Kuluttajaliitto – Konsumentförbundet](https://fi.wikipedia.org/wiki/Kuluttajaliitto_%E2%80%93_Konsumentf%C3%B6rbundet)).

### Valiokunnat

#### [Talousvaliokunta](https://www2.eduskunta.fi/FI/valiokunnat/talousvaliokunta/Sivut/default.aspx) (TaV)

Talousvaliokunta käsittelee elinkeinoelämään ja talouden toimintaan liittyviä asioita. Sen toimialaan kuuluvat esimerkiksi yritystoimintaa, energiaa, teknologiaa, kilpailua ja kuluttajansuojaa koskeva lainsäädäntö. Valiokunta käsittelee myös rahoitus- ja arvopaperimarkkinoita, valtion omistajapolitiikkaa sekä Suomen Pankkia ja Sitran toimintaa koskevia asioita.

Toimialaan kuuluvat:

- elinkeinot ja toimivat markkinat,
- yritysmuotoja koskeva lainsäädäntö,
- energia-asiat,
- teknologiaan ja tekniseen turvallisuuteen liittyvät asiat,
- kilpailu- ja kuluttajansuojalainsäädäntö,
- kirjanpito ja tilintarkastus,
- yksityinen vakuutustoiminta,
- rahoitus- ja arvopaperimarkkinalainsäädäntö,
- valtion omistajapolitiikkaa ja valtion yhtiöiden omistusta koskevat asiat,
- Suomen Pankki ja sen valtuutettujen kertomus ja
- Suomen itsenäisyyden juhlarahasto (Sitra) ja sen kertomus.

#### [Maa- ja metsätalousvaliokunta](https://www2.eduskunta.fi/FI/valiokunnat/maa-ja-mets%C3%A4talousvaliokunta/Sivut/default.aspx)​ (MmV)

Maa- ja metsätalousvaliokunta käsittelee maatalouteen, metsätalouteen ja maaseudun kehittämiseen liittyviä asioita. Sen toimialaan kuuluvat elintarviketurvallisuus, eläinten terveys ja hyvinvointi sekä kasvinterveys. Valiokunta käsittelee myös kalataloutta, riista- ja porotaloutta, kiinteistö- ja maanmittausasioita, vesitaloutta sekä ilmastonmuutokseen sopeutumiseen liittyviä kysymyksiä.

Toimialaan kuuluvat:

- maa- ja metsätalous sekä maaseudun kehittäminen,
- elintarvikkeet sekä maatalouden tuotantotarvikkeiden turvallisuus ja laatu,
- eläinlääkintähuolto, eläinten terveys ja hyvinvointi sekä kasvinterveys,
- kala-, riista- ja porotalous,
- maanmittaus, kiinteistöjä ja osakehuoneistoja koskevat kirjaamisasiat,
  paikkatietojen yhteiskäyttö ja kiinteistönmuodostus,
- vesitalous ja
- ilmastonmuutokseen sopeutuminen.

#### [Ympäristövaliokunta](https://www2.eduskunta.fi/FI/valiokunnat/ymparistovaliokunta/Sivut/default.aspx) (YmV)

Ympäristövaliokunta käsittelee ympäristönsuojeluun ja kestävään kehitykseen liittyviä asioita. Sen toimialaan kuuluvat ilmasto- ja ympäristöpolitiikka, luonnonsuojelu sekä vesien ja merien suojelu. Lisäksi valiokunta käsittelee maankäyttöä, rakentamista ja asuntopolitiikkaa sekä kulttuuriympäristön ja rakennusperinnön suojelua.

Toimialaan kuuluvat:

- ympäristönsuojelu ja jätehuolto, ilmastopolitiikka sekä meren- ja
  vesiensuojelu,
- luonnon monimuotoisuus ja luonnonsuojelu,
- kaavoitus, rakentaminen ja maankäyttö, kulttuuriympäristön ja
  rakennusperinnön hoito ja rakennussuojelu,
- asuntopolitiikka ja
- ilmastovuosikertomus.

Lähteet:

- Valiokuntien omat sivut (https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/ [Eduskunnan uudet sivut] ja https://www2.eduskunta.fi/FI/valiokunnat/Sivut/default.aspx [Eduskunnan vanhat sivut])
- Eduskunnan kanslia. (2023, February 23). Valiokuntaopas 2023. Eduskunta.fi. https://www.eduskunta.fi/api/assets/globalassets/pdft/eduskunnan-julkaisut/valiokuntaopas.pdf ISBN 978-951-53-3821-1 (pdf) | ISSN 1795-7230 (verkkojulkaisu)

### Lausuntopalvelu.fi

Lausuntopalvelu.fi on verkkopalvelu joka toteuttaa julkishallinnon lausuntomenettelyn sähköisenä palveluna.

Palvelun tarkoitus on tehostaa lausuntomenettelyä tarjoamalla kansalaisille, järjestöille ja viranomaisille yhdenmukainen verkkopalvelu jossa lausuntopyynnöt voidaan julkaista, antaa lausuntoja ja käsitellä annettuja lausuntoja.

Palvelulla on tarkoitus helpottaa lausuntomenettelyä, kansalaisvaikuttamista ja tiedonsaantia sekä lisätä valmistelun ja lausuntomenettelyn läpinäkyvyyttä ja laatua.

Palvelun käyttö on käyttäjille maksutonta. Palvelua ylläpitää oikeusministeriö ([lausuntopalvelu.fi: Ohjeet](https://www.lausuntopalvelu.fi/FI/Instruction/Instruction?section=About)).

## Tiedon lähteiden kartoitusta

### Kuluttajaliitto

- Kuluttajaliiton lausunnot, uusin ensin: https://www.kuluttajaliitto.fi/ajankohtaista/?3897474937=8&3257_sort=post_date%7Cdesc

### Valiokunnat

#### Talousvaliokunta

- Pääsivu (Valiokuntien pääsivut sisältävät linkit uusimpiin esityslistoihin, kokousten pöytäkirjoihin, viikkosuunnitelmiin ja kokoussuunnitelmiin.): https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/talousvaliokunta

- Käsittelyssä olevat asiat (uusin ensin): https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/talousvaliokunta/valiokunnissa-kasittelyssa-olevat-asiat?sort=laadintapvm_desc%2Cnimeke_asc

#### Maa- ja metsätalousvaliokunta

- Pääsivu: https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/maa-ja-metsatalousvaliokunta

- Käsittelyssä olevat asiat: https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/maa-ja-metsatalousvaliokunta/valiokunnissa-kasittelyssa-olevat-asiat?sort=laadintapvm_desc%2Cnimeke_asc

#### Ympäristövaliokunta

- Pääsivu: https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/ymparistovaliokunta

- Käsittelyssä olevat asiat, uusin ensin: https://www.eduskunta.fi/kansanedustajat-ja-toimielimet/valiokunnat/ymparistovaliokunta/valiokunnissa-kasittelyssa-olevat-asiat?sort=laadintapvm_desc%2Cnimeke_asc

### Lausuntopalvelu.fi

- Lausuntopyynnöt (uusin ensin): https://www.lausuntopalvelu.fi/FI/Proposal/List?sortby=PublishedOn&asc=False

- Sovellusrajapinta (API) ohjeet: https://www.lausuntopalvelu.fi/FI/Instruction/Instruction?section=OpenApi

- API: https://www.lausuntopalvelu.fi/api/v1/Lausuntopalvelu.svc/

- Kaikkien julkaistujen lausuntopyyntöjen yleiset tiedot: https://www.lausuntopalvelu.fi/api/v1/Lausuntopalvelu.svc/Proposals
