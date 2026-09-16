#!/usr/bin/env python3
"""Confronta due netlist KiCadXML e riporta le differenze di collegamento.

Uso:
    tools/netdiff.py <riferimento.xml> <zener.xml> [--eccezioni file] [--blocco NOME]

I componenti si accoppiano per riferimento (R12, C108): il lato Zener dichiara
gli stessi riferimenti dello schema annotato, perché l'annotatore di KiCad
rinumera tutto ciò che non è fissato (KTD3 del piano). I net si confrontano per
struttura, ignorando il nome: nello schema upstream i nodi interni sono anonimi
e prendono nomi autogenerati che cambiano a ogni rinumerazione.

Il footprint resta informativo e fuori dal confronto: i due lati lo scrivono in
notazioni disgiunte e in questa fase è comunque provvisorio (R14). I valori si
confrontano dopo normalizzazione (100n == 100nF == 0.1u).
"""

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

_MOLTIPLICATORI = {
    "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6,
    "m": 1e-3, "k": 1e3, "K": 1e3, "M": 1e6, "meg": 1e6, "g": 1e9, "G": 1e9,
}
_UNITA = ("f", "farad", "h", "henry", "ohm", "ohms", "Ω", "r", "v", "volt", "a", "hz")


def normalizza_valore(grezzo):
    """Riduce un valore a una forma confrontabile: numero più unità, o testo ripulito.

    Regge le notazioni che convivono nello stesso progetto: 100n, 100nF, 0.1uF,
    4k7, 1M5, 47, 47R. Quello che non è riconducibile a un numero torna come
    testo normalizzato, così i valori non numerici restano confrontabili fra loro.
    """
    if grezzo is None:
        return ""
    testo = grezzo.strip()
    if not testo:
        return ""

    ripulito = testo
    for unita in sorted(_UNITA, key=len, reverse=True):
        if ripulito.lower().endswith(unita):
            ripulito = ripulito[: -len(unita)]
            break
    ripulito = ripulito.strip()

    # Notazione con il moltiplicatore al posto della virgola: 4k7, 1M5, 2n2.
    infisso = re.fullmatch(r"(\d+)([pnuµμmkKMgG]|meg)(\d+)", ripulito)
    if infisso:
        intero, mult, decimali = infisso.groups()
        numero = float(f"{intero}.{decimali}") * _MOLTIPLICATORI[mult]
        return _formatta(numero)

    suffisso = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*([pnuµμmkKMgG]|meg)?", ripulito)
    if suffisso:
        numero, mult = suffisso.groups()
        valore = float(numero.replace(",", "."))
        if mult:
            valore *= _MOLTIPLICATORI[mult]
        return _formatta(valore)

    return " ".join(testo.lower().split())


def _formatta(numero):
    """Forma canonica di un numero: niente zeri di coda, niente notazione esponenziale ambigua."""
    return f"{numero:.12g}"


def leggi_netlist(percorso):
    """Estrae da una KiCadXML i componenti e il grafo pin -> net.

    Torna: (componenti, collegamenti) dove
      componenti[riferimento] = {"valore": ..., "footprint": ...}
      collegamenti[(riferimento, pin)] = identificativo del net (opaco)
    """
    radice = ET.parse(percorso).getroot()

    componenti = {}
    for comp in radice.iterfind("./components/comp"):
        riferimento = comp.get("ref")
        if riferimento is None:
            continue
        componenti[riferimento] = {
            "valore": (comp.findtext("value") or "").strip(),
            "footprint": (comp.findtext("footprint") or "").strip(),
        }

    collegamenti = {}
    for indice, net in enumerate(radice.iterfind("./nets/net")):
        codice = net.get("code") or str(indice)
        for nodo in net.iterfind("node"):
            riferimento, pin = nodo.get("ref"), nodo.get("pin")
            if riferimento is None or pin is None:
                continue
            collegamenti[(riferimento, pin)] = codice

    return componenti, collegamenti


def _classi(collegamenti):
    """Raggruppa i pin per net: l'insieme di pin è la struttura, il nome non conta."""
    per_net = defaultdict(set)
    for pin, net in collegamenti.items():
        per_net[net].add(pin)
    return {frozenset(pins) for pins in per_net.values()}


def confronta(riferimento, zener):
    """Confronta due netlist lette con leggi_netlist(). Torna la lista delle differenze."""
    comp_rif, coll_rif = riferimento
    comp_zen, coll_zen = zener
    differenze = []

    # 1. Accoppiamento per riferimento: un componente presente da un lato solo è
    #    un errore esplicito, non una differenza di collegamento.
    for mancante in sorted(set(comp_rif) - set(comp_zen)):
        differenze.append(("componente-assente-zener", mancante, ""))
    for aggiunto in sorted(set(comp_zen) - set(comp_rif)):
        differenze.append(("componente-assente-riferimento", aggiunto, ""))

    # 2. Valori, dopo normalizzazione. Il footprint non entra nel confronto.
    for riferimento_comp in sorted(set(comp_rif) & set(comp_zen)):
        a = normalizza_valore(comp_rif[riferimento_comp]["valore"])
        b = normalizza_valore(comp_zen[riferimento_comp]["valore"])
        if a != b:
            differenze.append(("valore-diverso", riferimento_comp, f"{a} != {b}"))

    # 3. Struttura dei collegamenti, a meno del nome del net.
    comuni = set(comp_rif) & set(comp_zen)
    classi_rif = {
        frozenset(p for p in classe if p[0] in comuni)
        for classe in _classi(coll_rif)
    }
    classi_zen = {
        frozenset(p for p in classe if p[0] in comuni)
        for classe in _classi(coll_zen)
    }
    classi_rif.discard(frozenset())
    classi_zen.discard(frozenset())

    for persa in sorted(classi_rif - classi_zen, key=_ordina_classe):
        differenze.append(("net-assente-zener", _mostra_classe(persa), ""))
    for aggiunta in sorted(classi_zen - classi_rif, key=_ordina_classe):
        differenze.append(("net-assente-riferimento", _mostra_classe(aggiunta), ""))

    return differenze


def _ordina_classe(classe):
    return sorted(classe)


def _mostra_classe(classe):
    return " ".join(f"{ref}.{pin}" for ref, pin in sorted(classe))


def leggi_eccezioni(percorso):
    """Legge le differenze dichiarate intenzionali: una per riga, `tipo soggetto`.

    Le righe vuote e quelle che iniziano con # sono commenti. Il verdetto che
    motiva l'eccezione sta nel documento a blocchi (R11), non qui.
    """
    if not percorso:
        return set()
    eccezioni = set()
    with open(percorso, encoding="utf-8") as sorgente:
        for riga in sorgente:
            riga = riga.split("#", 1)[0].strip()
            if riga:
                eccezioni.add(riga)
    return eccezioni


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("riferimento", help="netlist KiCadXML dello schema upstream annotato")
    parser.add_argument("zener", help="netlist KiCadXML generata dal sorgente Zener")
    parser.add_argument("--eccezioni", help="file delle differenze dichiarate intenzionali")
    parser.add_argument("--blocco", help="nome del blocco, per il rapporto")
    argomenti = parser.parse_args(argv)

    rif = leggi_netlist(argomenti.riferimento)
    zen = leggi_netlist(argomenti.zener)
    differenze = confronta(rif, zen)
    eccezioni = leggi_eccezioni(argomenti.eccezioni)

    intestazione = f"Blocco {argomenti.blocco}" if argomenti.blocco else "Confronto"
    print(f"{intestazione}: {len(rif[0])} componenti nel riferimento, {len(zen[0])} nello Zener")

    residue = []
    for tipo, soggetto, dettaglio in differenze:
        chiave = f"{tipo} {soggetto}"
        marcatura = "[intenzionale] " if chiave in eccezioni else ""
        riga = f"  {marcatura}{tipo}: {soggetto}"
        if dettaglio:
            riga += f" ({dettaglio})"
        print(riga)
        if not marcatura:
            residue.append(chiave)

    # Il footprint resta fuori dal confronto ma dentro al rapporto (R14).
    diversi_footprint = [
        r for r in sorted(set(rif[0]) & set(zen[0]))
        if rif[0][r]["footprint"] != zen[0][r]["footprint"]
    ]
    if diversi_footprint:
        print(f"  informativo: {len(diversi_footprint)} footprint scritti in notazione diversa (non confrontati)")

    if residue:
        print(f"{len(residue)} differenze non spiegate")
        return 1
    print("nessuna differenza non spiegata")
    return 0


if __name__ == "__main__":
    sys.exit(main())
