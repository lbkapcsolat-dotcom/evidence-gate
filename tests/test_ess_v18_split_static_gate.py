import tempfile, unittest
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml=None
from scripts.ess_v18_split_static_gate import check

@unittest.skipIf(yaml is None,"PyYAML unavailable")
class SplitGateTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.p=Path(self.t.name)/"producer.yml"
        self.c=Path(self.t.name)/"consumer.yml"
        self.p.write_text("""name: producer
on:
  workflow_dispatch:
permissions:
  contents: read
  actions: read
jobs:
  producer:
    steps:
      - uses: actions/upload-artifact@v4
""")
        self.c.write_text("""name: consumer
on:
  workflow_dispatch:
permissions:
  contents: read
  actions: read
jobs:
  consumer:
    steps:
      - uses: actions/checkout@v4
      - run: |
          python3 -m scripts.ess_v18_provider_native_fetch
          python3 -m scripts.ess_v18_consumer_preflight_adapter
          python3 -m scripts.ess_v18_zip_payload_custody
""")
    def test_positive(self):
        self.assertEqual(check(self.p,self.c),"PASS_SPLIT_STATIC_STRUCTURE")
    def test_same_run_dependency(self):
        self.c.write_text(self.c.read_text().replace("  consumer:\n","  consumer:\n    needs: producer\n"))
        with self.assertRaisesRegex(ValueError,"HOLD_SAME_RUN_DEPENDENCY"):check(self.p,self.c)
    def test_missing_fetch(self):
        self.c.write_text(self.c.read_text().replace("scripts.ess_v18_provider_native_fetch","missing"))
        with self.assertRaisesRegex(ValueError,"HOLD_NATIVE_FETCH"):check(self.p,self.c)
    def test_missing_custody(self):
        self.c.write_text(self.c.read_text().replace("scripts.ess_v18_zip_payload_custody","missing"))
        with self.assertRaisesRegex(ValueError,"HOLD_ZIP_CUSTODY"):check(self.p,self.c)
    def test_extra_consumer_job(self):
        self.c.write_text(self.c.read_text()+"  unexpected: {}\n")
        with self.assertRaisesRegex(ValueError,"HOLD_CONSUMER_JOB_SET"):check(self.p,self.c)
    def test_missing_manual_event(self):
        self.c.write_text(self.c.read_text().replace("workflow_dispatch:","push:"))
        with self.assertRaisesRegex(ValueError,"HOLD_MANUAL_DISPATCH"):check(self.p,self.c)

if __name__=="__main__":unittest.main()
