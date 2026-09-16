#!/usr/bin/env python3
"""Test di tools/netdiff.py — i casi sono quelli elencati in U3 del piano.

Esecuzione: python3 -m unittest discover -s tools -p 'test_*.py'
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import netdiff  # noqa: E402


def netlist_xml(componenti, nets):
    """Costruisce una KiCadXML minima ma della stessa forma di quella vera.

    componenti: lista di (ref, valore, footprint)
    nets: lista di (nome, [(ref, pin), ...])
    """
    righe = ['<?xml version="1.0" encoding="UTF-8"?>', '<export version="E">', "  <components>"]
    for ref, valore, footprint in componenti:
        righe.append(f'    <comp ref="{ref}">')
        righe.append(f"      <value>{valore}</value>")
        righe.append(f"      <footprint>{footprint}</footprint>")
        righe.append("    </comp>")
    righe.append("  </components>")
    righe.append("  <nets>")
    for indice, (nome, nodi) in enumerate(nets, start=1):
        righe.append(f'    <net code="{indice}" name="{nome}">')
        for ref, pin in nodi:
            righe.append(f'      <node ref="{ref}" pin="{pin}"/>')
        righe.append("    </net>")
    righe.append("  </nets>")
    righe.append("</export>")
    return "\n".join(righe)


class Base(unittest.TestCase):
    def setUp(self):
        self.temporanei = []

    def tearDown(self):
        for percorso in self.temporanei:
            os.unlink(percorso)

    def scrivi(self, contenuto):
        handle, percorso = tempfile.mkstemp(suffix=".xml")
        with os.fdopen(handle, "w", encoding="utf-8") as sorgente:
            sorgente.write(contenuto)
        self.temporanei.append(percorso)
        return percorso

    def differenze(self, xml_a, xml_b):
        a = netdiff.leggi_netlist(self.scrivi(xml_a))
        b = netdiff.leggi_netlist(self.scrivi(xml_b))
        return netdiff.confronta(a, b)


COMPONENTI = [
    ("R1", "47", "Resistor_THT:R_Axial_DIN0204"),
    ("C1", "100n", "Capacitor_THT:C_Disc_D3.0mm"),
    ("Q1", "2N3904", "Package_TO_SOT_THT:TO-92"),
]
NETS = [
    ("VCC", [("R1", "1"), ("C1", "1")]),
    ("Net-(Q1-Pad2)", [("R1", "2"), ("Q1", "2")]),
    ("GND", [("C1", "2"), ("Q1", "3")]),
]


class ConfrontoStrutturale(Base):
    def test_netlist_identiche_nessuna_differenza(self):
        xml = netlist_xml(COMPONENTI, NETS)
        self.assertEqual(self.differenze(xml, xml), [])

    def test_resistore_rimosso_riportato_col_riferimento(self):
        """Covers AE1: la differenza nomina il componente, non un nodo anonimo."""
        ridotti = [c for c in COMPONENTI if c[0] != "R1"]
        nets_ridotte = [
            ("VCC", [("C1", "1")]),
            ("Net-(Q1-Pad2)", [("Q1", "2")]),
            ("GND", [("C1", "2"), ("Q1", "3")]),
        ]
        differenze = self.differenze(netlist_xml(COMPONENTI, NETS), netlist_xml(ridotti, nets_ridotte))
        tipi = {tipo: soggetto for tipo, soggetto, _ in differenze}
        self.assertEqual(tipi.get("componente-assente-zener"), "R1")

    def test_net_rinominati_non_sono_differenze(self):
        """I nodi interni upstream sono anonimi: il nome non può essere la chiave."""
        rinominate = [
            ("N$1", NETS[0][1]),
            ("N$2", NETS[1][1]),
            ("N$3", NETS[2][1]),
        ]
        self.assertEqual(
            self.differenze(netlist_xml(COMPONENTI, NETS), netlist_xml(COMPONENTI, rinominate)), []
        )

    def test_due_pin_scambiati_riportati_entrambi(self):
        scambiate = [
            ("VCC", [("R1", "1"), ("Q1", "3")]),
            ("Net-(Q1-Pad2)", [("R1", "2"), ("Q1", "2")]),
            ("GND", [("C1", "2"), ("C1", "1")]),
        ]
        differenze = self.differenze(netlist_xml(COMPONENTI, NETS), netlist_xml(COMPONENTI, scambiate))
        tipi = [tipo for tipo, _, _ in differenze]
        self.assertGreaterEqual(tipi.count("net-assente-zener"), 2)
        self.assertGreaterEqual(tipi.count("net-assente-riferimento"), 2)

    def test_riferimento_presente_da_un_lato_solo_e_errore_esplicito(self):
        aggiunti = COMPONENTI + [("R99", "1k", "Resistor_SMD:R_0603")]
        nets_aggiunte = NETS + [("N$9", [("R99", "1"), ("R99", "2")])]
        differenze = self.differenze(netlist_xml(COMPONENTI, NETS), netlist_xml(aggiunti, nets_aggiunte))
        self.assertIn(("componente-assente-riferimento", "R99", ""), differenze)


class ValoriEFootprint(Base):
    def test_footprint_in_notazioni_diverse_non_sono_differenze(self):
        zener = [
            ("R1", "47", "package://stdlib/kicad-footprints/Resistor_SMD.pretty/R_0603_1608Metric.kicad_mod"),
            ("C1", "100n", "package://stdlib/kicad-footprints/Capacitor_SMD.pretty/C_0603_1608Metric.kicad_mod"),
            ("Q1", "2N3904", "package://stdlib/kicad-footprints/Package_TO_SOT_SMD.pretty/SOT-23.kicad_mod"),
        ]
        self.assertEqual(self.differenze(netlist_xml(COMPONENTI, NETS), netlist_xml(zener, NETS)), [])

    def test_valori_equivalenti_in_notazioni_diverse(self):
        zener = [("R1", "47R", ""), ("C1", "100nF", ""), ("Q1", "2N3904", "")]
        self.assertEqual(self.differenze(netlist_xml(COMPONENTI, NETS), netlist_xml(zener, NETS)), [])

    def test_valore_davvero_diverso_riportato(self):
        zener = [("R1", "470", ""), ("C1", "100n", ""), ("Q1", "2N3904", "")]
        differenze = self.differenze(netlist_xml(COMPONENTI, NETS), netlist_xml(zener, NETS))
        self.assertEqual([t for t, _, _ in differenze], ["valore-diverso"])

    def test_normalizzazione_delle_notazioni_ingegneristiche(self):
        for a, b in [("100n", "100nF"), ("0.1u", "100n"), ("4k7", "4700"), ("1M5", "1500000"), ("47", "47R")]:
            self.assertEqual(
                netdiff.normalizza_valore(a), netdiff.normalizza_valore(b), f"{a} dovrebbe valere {b}"
            )
        self.assertNotEqual(netdiff.normalizza_valore("47"), netdiff.normalizza_valore("470"))


class Eccezioni(Base):
    def test_differenza_dichiarata_intenzionale_non_fa_fallire(self):
        ridotti = [c for c in COMPONENTI if c[0] != "R1"]
        nets_ridotte = [
            ("VCC", [("C1", "1")]),
            ("Net-(Q1-Pad2)", [("Q1", "2")]),
            ("GND", [("C1", "2"), ("Q1", "3")]),
        ]
        riferimento = self.scrivi(netlist_xml(COMPONENTI, NETS))
        zener = self.scrivi(netlist_xml(ridotti, nets_ridotte))

        handle, eccezioni = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(handle, "w", encoding="utf-8") as sorgente:
            sorgente.write("# R1 tolto: verdetto «cambia», criterio spazio\n")
            sorgente.write("componente-assente-zener R1\n")
            for pin_a, pin_b in [("R1.1 C1.1", "VCC"), ("Q1.2 R1.2", "interno")]:
                sorgente.write(f"net-assente-zener {pin_a}\n")
        self.temporanei.append(eccezioni)

        codice = netdiff.main([riferimento, zener, "--eccezioni", eccezioni, "--blocco", "prova"])
        self.assertEqual(codice, 0, "una differenza dichiarata intenzionale non deve far fallire l'uscita")

    def test_differenza_non_dichiarata_fa_fallire(self):
        ridotti = [c for c in COMPONENTI if c[0] != "R1"]
        nets_ridotte = [("VCC", [("C1", "1")]), ("GND", [("C1", "2"), ("Q1", "3")])]
        riferimento = self.scrivi(netlist_xml(COMPONENTI, NETS))
        zener = self.scrivi(netlist_xml(ridotti, nets_ridotte))
        self.assertEqual(netdiff.main([riferimento, zener]), 1)


if __name__ == "__main__":
    unittest.main()
