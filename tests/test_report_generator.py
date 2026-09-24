"""Regression tests for the conservative panoramic report generator."""

import unittest

from app import ADULT_FDI_ORDER, build_final_report


class PanoramicReportGeneratorTests(unittest.TestCase):
    def test_fdi_order_and_individual_dbn_entries(self) -> None:
        report = build_final_report("18 IM H PR\n46 PR\n36 PIR\n15 TD\n25 TP", "", "")
        interpretation = report["HASIL INTERPRETASI"]

        positions = [interpretation.index(f"Gigi {tooth}") for tooth in ADULT_FDI_ORDER]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("Gigi 17: DBN.", interpretation)
        self.assertIn("Gigi 16: DBN.", interpretation)
        self.assertNotIn("Gigi 17, 16", interpretation)
        self.assertIn("Gigi 15: Restorasi sampai dentin.", interpretation)
        self.assertIn("Gigi 25: Restorasi sampai kamar pulpa.", interpretation)

    def test_pr_meaning_depends_on_impaction_and_pir_is_irreversible(self) -> None:
        report = build_final_report("18 IM H\n18 PR\n46 PR\n36 PIR", "", "")
        diagnosis = report["SUSPEK RADIODIAGNOSIS"]

        self.assertIn("Perikoronitis pada gigi 18.", diagnosis)
        self.assertIn("Pulpitis reversibel pada gigi 46.", diagnosis)
        self.assertIn("Pulpitis irreversibel pada gigi 36.", diagnosis)

    def test_identical_findings_are_combined_without_unsupported_details(self) -> None:
        report = build_final_report("16 TD\n26 TD", "", "")
        full_report = "\n".join(report.values()).lower()

        self.assertIn("gigi 16, 26: restorasi sampai dentin", full_report)
        for unsupported in ("karies dalam", "ukuran lesi", "kegagalan", "ekstraksi", "perawatan saluran akar"):
            self.assertNotIn(unsupported, full_report)
        self.assertNotIn("SARAN", report)

    def test_sections_are_separate_and_formally_named(self) -> None:
        report = build_final_report("48 IM V", "", "")
        self.assertEqual(list(report), ["HASIL INTERPRETASI", "SUSPEK RADIODIAGNOSIS"])


if __name__ == "__main__":
    unittest.main()
