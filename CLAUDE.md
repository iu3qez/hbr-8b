# CLAUDE.md — HBR/8B

Transceiver QRP CW per le bande HF. Questo repository nasce come fork del
progetto di R2AUK e sta diventando una build personale: **lo schema upstream è
una base, non la specifica**.

Prima di toccare qualcosa:

- `STRATEGY.md` — perché il progetto esiste, cosa si tiene e cosa si cambia.
- `docs/plans/` — il piano di lavoro corrente, con le unità U1-U10.
- `docs/blocchi.md` — il documento a blocchi: catena del segnale, budget,
  interfacce, verdetti. È il riferimento tecnico del progetto.

## Regole sempre valide

- **Gli MPN li sceglie Simo** (magazzino LCSC): mai inventarli.
- **I footprint si prendono dal datasheet o da `easyeda2kicad`**, mai a memoria.
  Minimo 0603: niente di più piccolo, per saldabilità a mano.
- **I footprint di questa fase sono provvisori** e non vincolano il layout. I
  default SMD dei generics della stdlib non si usano su componenti RF,
  magnetici o di potenza. Ogni impronta assegnata va in
  `docs/footprint-da-rivedere.md`.
- **I simboli devono essere in formato KiCad 10** (`(version 20251024)` o
  successiva): `pcb apply schematic` rifiuta i più vecchi. Quelli ripresi da
  altri progetti o generati da `easyeda2kicad` passano per
  `kicad-cli sym upgrade`.
- **Sui blocchi trascritti dall'upstream, i riferimenti dei componenti
  restano identici a quelli dello schema annotato** (`R12`, `C108`): sono la
  chiave con cui `tools/netdiff.py` accoppia i due lati.
- **Niente file destinati a durare in `/tmp`**: quello che deve sopravvivere
  va committato.

## Struttura

- `schematic/` — schema upstream KiCad 5, invariato. `schematic/converted/`
  contiene la conversione annotata, che è il riferimento ufficiale.
- `components/`, `modules/`, `boards/hbr8b/` — sorgente Zener (`pcb build`).
  Ogni blocco da confrontare con l'upstream è una board a sé sotto
  `boards/hbr8b/blocchi/`, perché `pcb apply schematic` scrive il `.kicad_sch`
  solo per un file che dichiara `Board(...)`.
- `firmware/` — firmware upstream, non toccato in questa fase.
- `tools/` — script di verifica.
