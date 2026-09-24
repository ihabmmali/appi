import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("workflow_checker", Path(__file__).resolve().parents[1] / "tools/check_workflow.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

TASK = """---
id: TEST-1
role: triage
status: proposed
delivery: not-applicable
verification: pending
owner: unassigned
base_commit: unset
artifact: none
---
# TEST-1
"""


class WorkflowValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "docs/tasks/TEST-1.md"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(TASK + "".join("\n## " + name + "\nRecorded.\n" for name in checker.SECTIONS))
        (self.root / "KNOWN_ISSUES.md").write_text("| TEST-1 | proposed | triage | [Task](docs/tasks/TEST-1.md) |\n")

    def change(self, old, new):
        self.path.write_text(self.path.read_text().replace(old, new))

    def test_valid_record(self):
        self.assertEqual(checker.validate(self.root), [])

    def test_invalid_status(self):
        self.change("status: proposed", "status: invented")
        self.assertTrue(any("invalid status" in e for e in checker.validate(self.root)))

    def test_index_drift(self):
        self.change("role: triage", "role: research")
        self.assertTrue(any("index status/role mismatch" in e for e in checker.validate(self.root)))

    def test_missing_metadata_does_not_crash(self):
        self.change("status: proposed\n", "")
        self.assertTrue(any("missing status" in e for e in checker.validate(self.root)))

    def test_done_without_verification(self):
        self.change("status: proposed", "status: done")
        self.assertTrue(any("done requires" in e for e in checker.validate(self.root)))

    def test_release_without_artifact(self):
        self.change("delivery: not-applicable", "delivery: released")
        self.assertTrue(any("released requires artifact" in e for e in checker.validate(self.root)))

    def test_broken_local_link(self):
        self.path.write_text(self.path.read_text() + "\n[Missing](missing.md)\n")
        self.assertTrue(any("broken local link" in e for e in checker.validate(self.root)))

    def test_valid_done_evidence(self):
        self.change("status: proposed", "status: done")
        self.change("verification: pending", "verification: passed")
        self.change("owner: unassigned", "owner: test-session")
        self.change("base_commit: unset", "base_commit: " + "a" * 40)
        (self.root / "KNOWN_ISSUES.md").write_text("| TEST-1 | done | triage | [Task](docs/tasks/TEST-1.md) |\n")
        self.assertEqual(checker.validate(self.root), [])
