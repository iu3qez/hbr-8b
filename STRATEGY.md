---
name: HBR/8B (IU3QEZ build)
last_updated: 2026-09-13
---

# HBR/8B (IU3QEZ build) Strategy

## Purpose

Opero in modo minimale e la mia passione è l'autocostruzione: voglio un transceiver CW QRP tutto mio che sostituisca il KX2 sul campo. Il nodo è che il KX2 fissa un'asticella alta di praticità, HBR/8B - buona base, derivata da EMRFD - ha molti punti da migliorare, e tanti progetti in passato (anche questo) si sono arenati per errori banali: sbroglio, schema, impronte, reperibilità. Questa volta non deve succedere.

## Positioning

Reuse piuttosto che rifare: le funzioni commodity (clock, MCU, amplificatore audio, ricarica LiPo) le fanno moduli commerciali; le parti critiche o da mettere a punto stanno su PCB dedicate innestabili, senza fili volanti, così si rifanno senza rifare il rig. Ogni parte deve guadagnarsi il posto su spazio, consumo, costo e montabilità a mano, e deve essere reperibile oggi. Niente va in fabbricazione senza essere stato verificato.

## Users

**Primary:** IU3QEZ in attivazione SOTA minimale con antenne non risonanti - lo assume per fare QSO CW dalla vetta portando il minimo indispensabile, accordando sul posto, senza rimpiangere il KX2.

## Boundaries

- Solo CW: niente SSB né modi digitali.
- Display definitivo rimandato alla fase 2; in fase 1 display volante.
- HBR/8B upstream è una base, non la specifica: le sue scelte si tengono solo se passano i criteri sopra.

_Resist a change when:_ riprogetta ciò che un modulo commerciale reperibile già fa, aggiunge parti che non si guadagnano il posto su spazio, consumo o montabilità, oppure va in fabbricazione saltando la verifica.

## Key metrics

- **Respin per errori banali** - PCB da rifare per errori di schema, sbroglio, impronte o componenti introvabili; obiettivo zero, conteggiato per ogni scheda ordinata.
- **Filtro IF** - banda 300-400 Hz, sweet spot 400 Hz, con la topologia meno problematica da mettere a punto; banda misurata + ascolto.
- **QSK** - commutazione a diodi PIN (anche 1N4007), istantanea, senza thump udibile; ascolto in cuffia.
- **Audio** - altoparlante front-facing, più grande di una moneta da 1 €; feeling operatore.

## Tracks

### Base a moduli commerciali

Scheda madre che ospita moduli commerciali per clock, MCU, amplificatore audio, ricarica LiPo.

_Why it serves the approach:_ non si riprogetta ciò che esiste già, è reperibile ed è collaudato.

### Blocchi critici su PCB innestabili

Filtro IF, BPF/LPF, PA con switch T/R QSK, su schede dedicate collegate in place (qui sparisce gran parte dei relè).

_Why it serves the approach:_ ciò che va messo a punto o rifatto si isola e si sostituisce senza toccare il resto.

### Integrazione SOTA

Case, ATU manuale per antenne non risonanti, altoparlante frontale, alimentazione LiPo.

_Why it serves the approach:_ senza questo non sostituisce il KX2 nello zaino.

### Verifica prima di fabbricare

Il gate prima di ogni ordine PCB: ricalcolo di guadagni e margini per ogni blocco (annotati sullo schema), ERC/DRC, impronte controllate sul datasheet, BOM verificata come reperibile. Schemi come codice in Zener, con il tool `pcb` di Diode.

_Why it serves the approach:_ i blocchi innestabili si rifanno a basso costo solo se non si rifanno per errori banali; schemi versionabili e moduli Zener riusabili servono sia al reuse sia alla verifica.
