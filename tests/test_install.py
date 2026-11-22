"""Installers: copy, status, update and graph. Runs install.ps1 on Windows and install.sh elsewhere."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = ROOT / "skills" / "powerbi-architect" / "SKILL.md"
VERSION = re.search(r'version:\s*"([^"]+)"', SKILL_MD.read_text(encoding="utf-8")).group(1)
WINDOWS = os.name == "nt"
DESTS = (".claude/skills", ".github/skills", ".agents/skills")


def install(target: Path, *flags: str) -> subprocess.CompletedProcess:
    if WINDOWS:
        names = {"--no-graph": "-NoGraph", "--no-hooks": "-NoHooks", "--status": "-Status",
                 "--update": "-Update", "--force": "-Force"}
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
               str(ROOT / "install" / "install.ps1"), "-Target", str(target), *(names[f] for f in flags)]
    else:
        cmd = ["bash", str(ROOT / "install" / "install.sh"), str(target), *flags]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


@unittest.skipIf(not WINDOWS and shutil.which("bash") is None, "bash not available")
class TestInstaller(unittest.TestCase):
    def test_install_status_update(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            r = install(repo, "--no-graph")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            for dest in DESTS:
                self.assertTrue((repo / dest / "powerbi-architect" / "SKILL.md").exists(), dest)
            self.assertFalse((repo / "powerbi-graph").exists())

            status = install(repo, "--status").stdout
            self.assertEqual(status.count("(up to date)"), 3, status)

            again = install(repo, "--no-graph")
            self.assertIn("exists, skipped", again.stdout)

            old = repo / ".claude/skills/powerbi-architect/SKILL.md"
            old.write_text(old.read_text(encoding="utf-8").replace(f'version: "{VERSION}"', 'version: "0.9.0"'),
                           encoding="utf-8")
            self.assertIn(f"update available: {VERSION}", install(repo, "--status").stdout)
            upd = install(repo, "--update", "--no-graph")
            self.assertEqual(upd.returncode, 0, upd.stdout + upd.stderr)
            self.assertIn(f"0.9.0 -> {VERSION}", upd.stdout)
            self.assertIn(f'version: "{VERSION}"', old.read_text(encoding="utf-8"))
            self.assertIn("Nothing to update", install(repo, "--update", "--no-graph").stdout)

    def test_install_builds_graph_on_a_pbip_repo(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            shutil.copytree(ROOT / "examples" / "contas-a-receber", repo / "contas-a-receber")
            r = install(repo, "--no-hooks")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((repo / "powerbi-graph" / "GRAPH_REPORT.md").exists(), r.stdout + r.stderr)
            self.assertIn("powerbi-graph", (repo / "AGENTS.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
