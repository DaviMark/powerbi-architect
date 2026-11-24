"""reconcile.py: the report's numbers against the source, row by row."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "powerbi-architect" / "scripts" / "reconcile.py"
sys.path.insert(0, str(SCRIPT.parent))
import reconcile  # noqa: E402

SOURCE = "Ano-Mês;Regional;Valor Vencido;% Vencido\njan/26;Sul;1.234,56;22,6%\njan/26;Norte;500,00;10,0%\n"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8")


class TestReconcile(unittest.TestCase):
    def files(self, d, report):
        a, b = Path(d) / "sql.csv", Path(d) / "dax.csv"
        a.write_text(SOURCE, encoding="utf-8")
        b.write_text(report, encoding="utf-8-sig")
        return a, b

    def test_matching_numbers_pass_in_any_locale(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = self.files(d, "dm_calendario[Ano-Mês],dm_regional[Regional],Valor Vencido,% Vencido\n"
                                 "jan/26,Sul,1234.56,0.226\njan/26,Norte,500.004,0.1\n")
            r = run(a, b, "--keys", "Ano-Mês,Regional")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("[ok]", r.stdout)

    def test_differences_and_missing_keys_fail(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = self.files(d, "Ano-Mês,Regional,Valor Vencido,% Vencido\njan/26,Sul,1334.56,0.226\n"
                                 "mar/26,Sul,10,0.1\n")
            r = run(a, b, "--keys", "Ano-Mês,Regional")
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("only in the source: jan/26 · Norte", r.stdout)
            self.assertIn("only in the report: mar/26 · Sul", r.stdout)
            self.assertIn("Valor Vencido: source 1234.56 · report 1334.56 (Δ +100)", r.stdout)

    def test_numbers_and_dax_template(self):
        self.assertEqual(reconcile.number("R$ 1.234,56", comma=True), 1234.56)
        self.assertEqual(reconcile.number("1,234.56"), 1234.56)
        self.assertAlmostEqual(reconcile.number("22,6%", comma=True), 0.226)
        self.assertIsNone(reconcile.number("(Blank)"))
        out = run("--dax", "Valor Vencido", "--by", "dm_regional[Regional]").stdout
        self.assertIn('"Valor Vencido", [Valor Vencido]', out)
        self.assertIn("GROUP BY Regional", out)


if __name__ == "__main__":
    unittest.main()
