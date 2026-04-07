# Complete iFAS Import Mapping: Majesty Export → iFAS Multi-Sheet Format

Complete mapping specification for migrating Majesty data to iFAS import format across all sheet types.
This document guides the transformation of Majesty export data into properly structured iFAS import sheets.

**Date:** 2026-03-24  
**Source Majesty Export:** xport_majesty_artikelstamm_2026_03_19.csv  
**Sample Template:** data/samplefile.xlsx (5 sheets + 1 reference sheet)

Legend for "Suggested treatment":
- keep empty: keep blank in export unless business says otherwise
- direct copy: copy from Majesty export field as-is (trimmed)
- derive: compute with business rule

| # | Beispielimport header | Majesty export candidate | Suggested treatment | Your decision |
|---:|---|---|---|---|
| 1 | Spalten |  | ignore technical/header helper column (can be removed from final mapping list) | IGNORE |
| 2 | Artikelnummer | artnr | Direct copy, trim; preserve leading zeros. | OK |
| 3 | Initvariante Identifikation |  | Keep empty. | EMPTY |
| 4 | Artikelstatus | sperreart | Derive: set `9` only if `sperreart` is NOT `1` and NOT `true`; otherwise set to `1` | CONFIRMED RULE |
| 5 | Bezeichnung 1 [de] | artbez1 | Direct copy. | OK |
| 6 | Bezeichnung 1 [en] |  | Keep empty per default. | CONFIRMED RULE |
| 7 | Bezeichnung 1 [fr] |  | Keep empty per default. | CONFIRMED RULE |
| 8 | Bezeichnung 1 [it] |  | Keep empty per default. | CONFIRMED RULE |
| 9 | Bezeichnung 2 [de] | artbez2 + artbez3 + artbezmem | Concatenate all, strip line breaks from artbezmem, separate with space if present | OK |
| 10 | Bezeichnung 2 [en] |  | Keep empty per default. | CONFIRMED RULE |
| 11 | Bezeichnung 2 [fr] |  | Keep empty per default. | CONFIRMED RULE |
| 12 | Bezeichnung 2 [it] |  | Keep empty per default. | CONFIRMED RULE |
| 13 | Suchbegriff 1 [de] | artsuch | Direct copy from `artsuch` (trim). | OK |
| 14 | Suchbegriff 1 [en] |  | Keep empty per default. | CONFIRMED RULE |
| 15 | Suchbegriff 1 [fr] |  | Keep empty per default. | CONFIRMED RULE |
| 16 | Suchbegriff 1 [it] |  | Keep empty per default. | CONFIRMED RULE |
| 17 | Suchbegriff 2 [de] | artsuch2 | Direct copy from `artsuch2` (trim) if present; otherwise empty. | OK |
| 18 | Suchbegriff 2 [en] |  | Keep empty per default. | CONFIRMED RULE |
| 19 | Suchbegriff 2 [fr] |  | Keep empty per default. | CONFIRMED RULE |
| 20 | Suchbegriff 2 [it] |  | Keep empty per default. | CONFIRMED RULE |
| 21 | Einkaufsartikel | const(1) | Boolean field; default value `1`. | CONFIRMED RULE |
| 22 | Verkaufsartikel | const(0) | Boolean field; default value `0`. | CONFIRMED RULE |
| 23 | Serviceartikel | const(0) | Boolean field; default value `0`. | CONFIRMED RULE |
| 24 | Produktionsartikel | zeichnr | Derive: `1` if `zeichnr` is not empty; `0` if empty. | CONFIRMED RULE |
| 25 | Auslaufartikel | const(0) | Boolean field; default value `0`. | CONFIRMED RULE |
| 26 | Freigabe Einkauf | const(1) | Boolean field; default value `1`. | CONFIRMED RULE |
| 27 | Freigabe Verkauf | const(0) | Boolean field; default value `0`. | CONFIRMED RULE |
| 28 | Freigabe Service | const(0) | Boolean field; default value `0`. | CONFIRMED RULE |
| 29 | Freigabe Produktion | const(1) | Boolean field; default value `1`. | CONFIRMED RULE |
| 30 | Freigabe Baugruppe | const(1) | Boolean field; default value `1`. | CONFIRMED RULE |
| 31 | Freigabe Stückliste | const(1) | Boolean field; default value `1`. | CONFIRMED RULE |
| 32 | Dienstleistungsartikel | const(0) | Boolean field; default value `0`. | CONFIRMED RULE |
| 33 | Topfartikel | const(0) | Boolean field; default value `0`. | CONFIRMED RULE |
| 34 | Textpositionsartikel | const(0) | Boolean field; default value `0`. | CONFIRMED RULE |
| 35 | Beschaffungsart | partlist(stulinr) + artnr | Derive: set value to `1` when a partlist exists with `stulinr == artnr`; otherwise set `6`. | CONFIRMED RULE |
| 36 | Beschaffungstyp | const(11) | Set fixed value `11` for all records. | CONFIRMED RULE |
| 37 | Steuermass | const(1) | Use fixed value `1` for all records (temporary default until tax logic is implemented). | CONFIRMED RULE |
| 38 | Vorsteuerunterteilung Einkauf | const(1) | Boolean field; default value `1`. | CONFIRMED RULE |
| 39 | Masseinheit Verkauf | const(1) | Numeric field; default value `1`. | CONFIRMED RULE |
| 40 | Gebindeinhalt Verkauf |  | Keep empty per default. | CONFIRMED RULE |
| 41 | Anzahl Artikel pro Verkaufs-Masseinheit | const(1) | Numeric field; default value `1`. | CONFIRMED RULE |
| 42 | Nettogewicht (kg) |  | keep empty. | CONFIRMED RULE |
| 43 | Masseinheit Produktion | peinheit / const(1) | Use `peinheit`; if empty, fallback to `1`. | CONFIRMED RULE |
| 44 | Nettogewicht Produktion |  | keep empty. | CONFIRMED RULE |
| 45 | Gebindeinhalt Produktion |  | keep empty. | CONFIRMED RULE |
| 46 | Umrechnungsfaktor PE/LVE | const(1) | Numeric field; default value `1`. | CONFIRMED RULE |
| 47 | Masseinheit Einkauf | peinheit | Direct copy from `peinheit`. | CONFIRMED RULE |
| 48 | Gebindeinhalt Einkauf |  | keep empty. | CONFIRMED RULE |
| 49 | Anzahl Artikel pro Einkaufs-Masseinheit | const(1) | Numeric field; default value `1`. | CONFIRMED RULE |
| 50 | Nettogewicht Einkauf (kg) |  | keep empty. | CONFIRMED RULE |
| 51 | Masseinheit Lager | peinheit | Direct copy from `peinheit`. | CONFIRMED RULE |
| 52 | Anzahl Artikel pro Lager-Masseinheit | const(1) | Numeric field; default value `1`. | CONFIRMED RULE |
| 53 | Lieferantennummer | letzt_lief (= liefnr) + supplier-name lookup | Source field in xport is `letzt_lief` which contains the Majesty `liefnr`. Derive: take `letzt_lief` -> lookup company name in `Lieferanten_Majesty.csv`; find company in `Adressliste_iFAS.csv`; write matched `Nummer` from iFAS address list. Use candidate list + manual review for ambiguous names. | CONFIRMED RULE |
| 54 | Mindestbestellmenge Einkauf |  | keep empty. | CONFIRMED RULE |
| 55 | Optimale Losgrösse Einkauf |  | keep empty. | CONFIRMED RULE |
| 56 | Spezifisches Gewicht |  | keep empty. | CONFIRMED RULE |
| 57 | Inventurart | const(1) | Default value `1`. | CONFIRMED RULE |
| 58 | Inventur Periodizität (Tage) |  | keep empty. | CONFIRMED RULE |
| 59 | Stückliste |  | keep empty (initial proposal; confirm needed/optional) |  |
| 60 | Stückliste auflösen in Belegen |  | keep empty (initial proposal; confirm needed/optional) |  |
| 61 | Stückliste auflösen in Produktionsauftrag |  | keep empty (initial proposal; confirm needed/optional) |  |
| 62 | Stücklistenpositionen MW-Aktiv |  | keep empty (initial proposal; confirm needed/optional) |  |
| 63 | Preis auf Stücklistenpositionen |  | keep empty (initial proposal; confirm needed/optional) |  |
| 64 | Stücklistenpositionen fakturieren |  | keep empty (initial proposal; confirm needed/optional) |  |
| 65 | Arbeitsplan |  | keep empty (initial proposal; confirm needed/optional) |  |
| 66 | Ist MW Aktiv | const(1) | Default value `1`. | CONFIRMED RULE |
| 67 | Lagerbewertungsverfahren | const(1) | Default value `1`. | CONFIRMED RULE |
| 68 | Seriennummern |  | keep empty (initial proposal; confirm needed/optional) |  |
| 69 | Vergabeart Serien |  | keep empty (initial proposal; confirm needed/optional) |  |
| 70 | Nummernkreis Serien |  | keep empty (initial proposal; confirm needed/optional) |  |
| 71 | Mit Chargen |  | keep empty (initial proposal; confirm needed/optional) |  |
| 72 | Vergabeart Chargen |  | keep empty (initial proposal; confirm needed/optional) |  |
| 73 | Nummernkreis Chargen |  | keep empty (initial proposal; confirm needed/optional) |  |
| 74 | Verfalltage [Tage] |  | keep empty (initial proposal; confirm needed/optional) |  |
| 75 | Preiseinheit Einkauf | const(1) | Default value `1`. | CONFIRMED RULE |
| 76 | Umrechnungsfaktor Preise Einkauf | const(1) | Default value `1`. | CONFIRMED RULE |
| 77 | Preiseinheit Verkauf | const(1) | Default value `1`. | CONFIRMED RULE |
| 78 | Umrechnungsfaktor Preis Verkauf | const(1) | Default value `1`. | CONFIRMED RULE |
| 79 | Erlöskonto |  | keep empty (initial proposal; confirm needed/optional) |  |
| 80 | Erlöskonto Service |  | keep empty (initial proposal; confirm needed/optional) |  |
| 81 | Aufwandkonto |  | keep empty (initial proposal; confirm needed/optional) |  |
| 82 | Wareneingangkonto |  | keep empty (initial proposal; confirm needed/optional) |  |
| 83 | Warenaufwandkonto |  | keep empty (initial proposal; confirm needed/optional) |  |
| 84 | Warenaufwandkonto Service |  | keep empty (initial proposal; confirm needed/optional) |  |
| 85 | Warenaufwandkonto Produktion |  | keep empty (initial proposal; confirm needed/optional) |  |
| 86 | Warenbestandkonto |  | keep empty (initial proposal; confirm needed/optional) |  |
| 87 | Ware in Arbeit Konto Produktion |  | keep empty (initial proposal; confirm needed/optional) |  |
| 88 | Warenbestand Änderung Konto Produktion |  | keep empty (initial proposal; confirm needed/optional) |  |
| 89 | Preisdifferenz Konto Produktion |  | keep empty (initial proposal; confirm needed/optional) |  |
| 90 | Inventurdifferenzkonto |  | keep empty (initial proposal; confirm needed/optional) |  |
| 91 | Verschrottungskonto |  | keep empty (initial proposal; confirm needed/optional) |  |
| 92 | Kostenstelle Erlös |  | keep empty (initial proposal; confirm needed/optional) |  |
| 93 | Kostenstelle Erlös Service |  | keep empty (initial proposal; confirm needed/optional) |  |
| 94 | Kostenstelle Aufwand |  | keep empty (initial proposal; confirm needed/optional) |  |
| 95 | Kostenstelle Inventur |  | keep empty (initial proposal; confirm needed/optional) |  |
| 96 | Kostenstelle Ware in Arbeit |  | keep empty (initial proposal; confirm needed/optional) |  |
| 97 | Preisdifferenz Kostenstelle Produktion |  | keep empty (initial proposal; confirm needed/optional) |  |
| 98 | EAN-13 Nummer |  | keep empty. | CONFIRMED RULE |
| 99 | Warengruppe | zeichnr -> `Waren-_Artikelgruppe.csv` (`Code`) -> `Warengruppe` | Derive from `zeichnr`: first match by first code block. If that does not identify a single row, use the next code block after the whitespace to disambiguate. Write matched `Warengruppe` to iFAS import. Fallback to `warengru` if no match. | CONFIRMED RULE |
| 100 | Artikelgruppe 1 | zeichnr -> `Waren-_Artikelgruppe.csv` (`Code`) -> `Artikelgruppe 1` | Derive from `zeichnr` with same logic as row 99: first code block, then second code block after whitespace if needed. Write matched `Artikelgruppe 1`. Fallback to `artgru1`, then `artgru` if no match. | CONFIRMED RULE |
| 101 | Artikelgruppe 2 | zeichnr -> `Waren-_Artikelgruppe.csv` (`Code`) -> `Artikelgruppe 2` | Derive from `zeichnr` with same logic as row 99: first code block, then second code block after whitespace if needed. Write matched `Artikelgruppe 2`. Fallback to `artgru2` if no match. | CONFIRMED RULE |
| 102 | Artikelgruppe 3 |  | keep empty. | CONFIRMED RULE |
| 103 | Artikelgruppe 4 |  | keep empty. | CONFIRMED RULE |
| 104 | Artikelgruppe 5 |  | keep empty. | CONFIRMED RULE |
| 105 | Artikelgruppe 6 |  | keep empty. | CONFIRMED RULE |
| 106 | Artikelgruppe 7 |  | keep empty. | CONFIRMED RULE |
| 107 | Artikelgruppe 8 |  | keep empty. | CONFIRMED RULE |
| 108 | Artikelgruppe 9 |  | keep empty. | CONFIRMED RULE |
| 109 | Artikelgruppe 10 |  | keep empty. | CONFIRMED RULE |
| 110 | Kontierungsgruppe | Lieferantennummer -> const(`Material Gruppe`) / const(`Material`) | If iFAS supplier code (`Lieferantennummer`) = `001199`, write `Material Gruppe`; otherwise write `Material`. | CONFIRMED RULE |
| 111 | Freier Text 1 |  | keep empty. | CONFIRMED RULE |
| 112 | Freier Text 2 |  | keep empty. | CONFIRMED RULE |
| 113 | Freier Text 3 |  | keep empty. | CONFIRMED RULE |
| 114 | Freier Text 4 |  | keep empty. | CONFIRMED RULE |
| 115 | Freier Text 5 |  | keep empty. | CONFIRMED RULE |
| 116 | Freier Text 6 |  | keep empty. | CONFIRMED RULE |
| 117 | Freier Text 7 |  | keep empty. | CONFIRMED RULE |
| 118 | Freier Text 8 |  | keep empty. | CONFIRMED RULE |
| 119 | Freier Text 9 |  | keep empty. | CONFIRMED RULE |
| 120 | Freier Text 10 | const(`Import_via_API_YYYY-MM-DD`) | Set to `Import_via_API_<current-date>` for each generated export run to support ERP filtering of API-imported products. | CONFIRMED RULE |
| 121 | Freier Text lokalisiert 1 [de] |  | keep empty. | CONFIRMED RULE |
| 122 | Freier Text lokalisiert 1 [en] |  | keep empty. | CONFIRMED RULE |
| 123 | Freier Text lokalisiert 1 [fr] |  | keep empty. | CONFIRMED RULE |
| 124 | Freier Text lokalisiert 1 [it] |  | keep empty. | CONFIRMED RULE |
| 125 | Freier Text lokalisiert 2 [de] |  | keep empty. | CONFIRMED RULE |
| 126 | Freier Text lokalisiert 2 [en] |  | keep empty. | CONFIRMED RULE |
| 127 | Freier Text lokalisiert 2 [fr] |  | keep empty. | CONFIRMED RULE |
| 128 | Freier Text lokalisiert 2 [it] |  | keep empty. | CONFIRMED RULE |
| 129 | Meldungskonfiguration |  | keep empty. | CONFIRMED RULE |
| 130 | Artikeltyp |  | keep empty. | CONFIRMED RULE |
| 131 | Alte System Nr. |  | keep empty. | CONFIRMED RULE |
| 132 | Nachfolger |  | keep empty. | CONFIRMED RULE |
| 133 | Zeichnungsindex | zeichindex | Direct copy. | CONFIRMED RULE |
| 134 | Zeichnungsnummer | zeichnr | Direct copy. | CONFIRMED RULE |
| 135 | Vorgänger |  | keep empty. | CONFIRMED RULE |
| 136 | Höhe (Dimension) |  | keep empty. | CONFIRMED RULE |
| 137 | Tiefe (Dimension) |  | keep empty. | CONFIRMED RULE |
| 138 | Länge (Dimension) |  | keep empty. | CONFIRMED RULE |
| 139 | Breite (Dimension) |  | keep empty. | CONFIRMED RULE |
| 145 | Wiederbeschaffungszeit | WBZ from lieferanten_ifas_mapping_auto.csv | Copy WBZ from lieferanten_ifas_mapping_auto.csv where liefnr matches the liefnr in Artikelstamm_Majesty_....csv | CONFIRMED RULE |
| 140 | Fläche |  | keep empty. | CONFIRMED RULE |
| 141 | Verpackungseinheit Code |  | keep empty. | CONFIRMED RULE |
| 142 | Zolltarifnummer |  | keep empty. | CONFIRMED RULE |
| 143 | Ursprungszeugnis |  | keep empty. | CONFIRMED RULE |
| 144 | Ursprungsland | ursprland | Normalize to expected country code if needed. | CONFIRMED RULE |
| 145 | Einbaumengen Code |  | keep empty. | CONFIRMED RULE |
| 146 | Verschnitt % |  | keep empty. | CONFIRMED RULE |
| 147 | Verschnitt fix |  | keep empty. | CONFIRMED RULE |
| 148 | Verschnitt Zuschnitt % |  | keep empty. | CONFIRMED RULE |
| 149 | Optimale Losgroesse PE |  | keep empty. | CONFIRMED RULE |
| 150 | MW-Preis (für aktuelle Org.einheit) | letzt_ek | Direct copy from `letzt_ek`. | CONFIRMED RULE |
| 151 | Ausblenden in Planung? |  | keep empty. | CONFIRMED RULE |
| 152 | Ist Vorlage Artikel? |  | keep empty. | CONFIRMED RULE |
| 153 | Streckengeschäftsart |  | keep empty. | CONFIRMED RULE |
| 154 | Zusatztextart 1
(ISZTAId) |  | keep empty (needs business decision). | REASSESS |
| 155 | Zusatztext 1 [de] |  | keep empty. | CONFIRMED RULE |
| 156 | Zusatztext 1 [en] |  | keep empty. | CONFIRMED RULE |
| 157 | Zusatztext 1 [fr] |  | keep empty. | CONFIRMED RULE |
| 158 | Zusatztext 1 [it] |  | keep empty. | CONFIRMED RULE |
| 159 | Zusatztextart 2
(ISZTAId) |  | keep empty. | CONFIRMED RULE |
| 160 | Zusatztext 2 [de] |  | keep empty. | CONFIRMED RULE |
| 161 | Zusatztext 2 [en] |  | keep empty. | CONFIRMED RULE |
| 162 | Zusatztext 2 [fr] |  | keep empty. | CONFIRMED RULE |
| 163 | Zusatztext 2 [it] |  | keep empty. | CONFIRMED RULE |
| 164 | Sind Zusatztexte RTF Text? 
(0 = nein, 1 = ja) |  | keep empty (needs business decision). | REASSESS |
| 165 | MW-Artikel |  | keep empty. | CONFIRMED RULE |
| 166 | Disponentencode |  | keep empty. | CONFIRMED RULE |
| 167 | Org.Einheit Identifier | const(JOS) | Use fixed value `JOS` for all records. | CONFIRMED RULE |
| 168 | Mindestbestellmenge Verkauf |  | keep empty. | CONFIRMED RULE |
| 169 | Optimale Losgrösse Verkauf |  | keep empty. | CONFIRMED RULE |

---

## Vorschlaege fuer optionale Sheets (Sample row 7)

Hinweis:
- Diese vier Sheets werden aktuell technisch angelegt, aber noch nicht inhaltlich befuellt.
- Die folgenden Vorschlaege sind als Start-Mapping gedacht (MVP), damit wir den Plan vervollstaendigen.

### Sheet: ArtikelDisposteuerungen

| # | Header (row 7) | Majesty export candidate | Suggested treatment | Your decision |
|---:|---|---|---|---|
| 1 | Spalten |  | ignore technical helper column | CONFIRMED |
| 2 | Artikelnummer | artnr | direct copy, trim | CONFIRMED |
| 3 | Dispositionsbereich | const(02) | fixed default `02` | CONFIRMED |
| 4 |  Wiederbeschaffungszeit | WBZ from lieferanten_ifas_mapping_auto.csv | Copy WBZ from lieferanten_ifas_mapping_auto.csv where liefnr matches the liefnr in Artikelstamm_Majesty_....csv | CONFIRMED RULE |
| 5 | Sicherheitsbestand LE |  | keep empty (REASSESS) | CONFIRMED |
| 6 | Meldebestand LE |  | keep empty (REASSESS) | CONFIRMED |
| 7 | Maximalbestand LE |  | keep empty (REASSESS) | CONFIRMED |
| 8 | Standard Lagerort/Platz | const(Jost) | fixed default `Jost` | CONFIRMED |
| 9 | Org.Einheit Identifier | const(JOS) | fixed value `JOS` | CONFIRMED |
| 10 | (leer) |  | ignore empty helper column | CONFIRMED |
| 11 | INFO |  | ignore info/helper column | CONFIRMED |

### Sheet: Artikel-Lieferantendaten

| # | Header (row 7) | Majesty export candidate | Suggested treatment | Your decision |
|---:|---|---|---|---|
| 1 | Spalten |  | ignore technical helper column | CONFIRMED |
| 2 | Artikelnummer | artnr | direct copy | CONFIRMED |
| 3 | Lieferantennummer | letzt_lief + supplier-name lookup | derive identisch zu Artikelstamm row 53 | CONFIRMED |
| 4 | Artikelnummer Lieferant | artnrlief | direct copy; no row swaps | CONFIRMED |
| 5 | Artikelbezeichnung Lieferant | artbez1 + artbez2 | concatenate in this order; no row swaps | CONFIRMED |
| 6 | Artikel-Zusatz-Bezeichnung Lieferant | artbez3 + artbezmem | concatenate in this order; strip line breaks from artbezmem; no row swaps | CONFIRMED |
| 7 | Artikelbemerkung Lieferant |  | keep empty | CONFIRMED |
| 8 | Hersteller |  | keep empty (REASSESS if source field available) | CONFIRMED |
| 9 | Bewertungskatalog |  | keep empty | CONFIRMED |
| 10 | Masseinheit Einkauf Lieferant | peinheit | direct copy | CONFIRMED |
| 11 | Preiseinheit Lieferant | const(1) | fixed `1` | CONFIRMED |
| 12 | Umrechnungsfaktor Preis | const(1) | fixed `1` | CONFIRMED |
| 13 | Umrechnungsfaktor EE/LVE | const(1) | fixed `1` | CONFIRMED |
| 14 | Zeichnungs Nr. Lieferant |  | keep empty | CONFIRMED |
| 15 | Mindestebestellmenge EE |  | keep empty | CONFIRMED |
| 16 | Optimale Losgrösse EE |  | keep empty | CONFIRMED |
| 17 | Kontaktnummer Kontakt Lieferant |  | keep empty | CONFIRMED |
| 18 | Verpackungseinheit |  | keep empty | CONFIRMED |
| 19 | Ursprungszeugnis |  | keep empty | CONFIRMED |
| 20 | Zolltarifnummer |  | keep empty | CONFIRMED |
| 21 | Ursprungsland | ursprland | direct copy (optional country code normalize) | CONFIRMED |
| 22 | Org.Einheit Identifier | const(JOS) | fixed value `JOS` | CONFIRMED |

### Sheet: Artikel-Kundendaten

| # | Header (row 7) | Majesty export candidate | Suggested treatment | Your decision |
|---:|---|---|---|---|
| 1 | Spalten |  | ignore technical helper column | SUGGESTED |
| 2 | Artikelnummer | artnr | direct copy | SUGGESTED |
| 3 | Kundennummer |  | keep empty (requires customer master mapping) | SUGGESTED |
| 4 | Artikelnummer Kunde |  | keep empty | SUGGESTED |
| 5 | Artikelbezeichnung Kunde | artbez1 | direct copy as initial fallback | SUGGESTED |
| 6 | Artikel-Zusatz-Bezeichnung Kunde | artbez2 | direct copy as initial fallback | SUGGESTED |
| 7 | Artikelbemerkung Kunde |  | keep empty | SUGGESTED |
| 8 | Hersteller |  | keep empty | SUGGESTED |
| 9 | Bewertungskatalog |  | keep empty | SUGGESTED |
| 10 | Masseinheit Verkauf des Kunden | const(1) | fixed `1` (aligned with Masseinheit Verkauf) | SUGGESTED |
| 11 | Preiseinheit Kunde | const(1) | fixed `1` | SUGGESTED |
| 12 | Umrechnungsfaktor Preis | const(1) | fixed `1` | SUGGESTED |
| 13 | Umrechnungsfaktor VK/LVE | const(1) | fixed `1` | SUGGESTED |
| 14 | Zeichnungs Nr. Kunde | zeichnr | direct copy as fallback | SUGGESTED |
| 15 | Kontaktnummer Kontakt Kunde |  | keep empty | SUGGESTED |
| 16 | VerpackungseinheitCode |  | keep empty | SUGGESTED |
| 17 | Org.Einheit Identifier | const(JOS) | fixed value `JOS` | SUGGESTED |

### Sheet: Artikel-Qualitaetsmerkmale

| # | Header (row 7) | Majesty export candidate | Suggested treatment | Your decision |
|---:|---|---|---|---|
| 1 | Spalten |  | ignore technical helper column | SUGGESTED |
| 2 | Artikelnummer | artnr | direct copy | SUGGESTED |
| 3 | Sortierung | const(1) | fixed default `1` if row exists | SUGGESTED |
| 4 | fuer Charge? (0=nein, 1=ja) | const(0) | default `0` | SUGGESTED |
| 5 | Ist Inaktiv? (0=nein, 1=ja) | const(0) | default `0` | SUGGESTED |
| 6 | Q-Merkmal Eigenschaft-Cd |  | keep empty (requires quality master) | SUGGESTED |
| 7 | Masseinheit-Cd |  | keep empty | SUGGESTED |
| 8 | Spezifikation-Code |  | keep empty | SUGGESTED |
| 9 | Q-Merkmal Status |  | keep empty | SUGGESTED |
| 10 | Sollwert |  | keep empty | SUGGESTED |
| 11 | Von Sollwert |  | keep empty | SUGGESTED |
| 12 | Bis Sollwert |  | keep empty | SUGGESTED |
| 13 | Minus-Toleranz |  | keep empty | SUGGESTED |
| 14 | Plus-Toleranz |  | keep empty | SUGGESTED |
| 15 | Prozentuale Toleranz? (0=nein, 1=ja) | const(0) | default `0` | SUGGESTED |
| 16 | Hinweise |  | keep empty | SUGGESTED |

---

## Finalisierte Entscheidungen

- Entscheidung 1: Initial mindestens 1 Zeile je Artikel fuer Dispo-/Lieferanten-/Kundendaten erzeugen.
- Entscheidung 2: `Org.Einheit Identifier` in allen optionalen Sheets fest auf `JOS`.
