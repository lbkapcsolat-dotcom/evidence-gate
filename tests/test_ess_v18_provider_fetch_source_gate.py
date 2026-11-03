"""Offline negative tests for provider native fetch identity and ZIP pre-extraction gates.
Never performs a network call or a workflow dispatch.
"""
import ast
import unittest
from pathlib import Path

SOURCE=Path("scripts/ess_v18_provider_native_fetch.py")
WORKFLOW=".github/workflows/ess-openshell-v18-producer-only.yml"

class ProviderFetchSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SOURCE.read_text()
        cls.tree=ast.parse(cls.source)
    def test_exact_producer_workflow_fence(self):
        self.assertIn('workflow==".github/workflows/ess-openshell-v18-producer-only.yml"',self.source)
    def test_producer_run_status_and_identity_guards(self):
        for code in ["PRODUCER_ID","NOT_TWO_RUNS","PRODUCER_SHA","PRODUCER_REPOSITORY","PRODUCER_WORKFLOW","PRODUCER_EVENT","PRODUCER_ATTEMPT"]:
            with self.subTest(code=code):self.assertIn('"'+code+'"',self.source)
    def test_archive_and_expansion_limits(self):
        for code in ["ARCHIVE_SIZE_LIMIT","ZIP_TOTAL_SIZE_LIMIT","ZIP_MEMBER_UNSAFE","ZIP_MEMBER_SET"]:
            with self.subTest(code=code):self.assertIn('"'+code+'"',self.source)
    def test_dynamic_pin_exports(self):
        for name in ["PINNED_V1_8_SOURCE_RUN","PINNED_V1_8_SOURCE_SHA","PINNED_V1_8_ARTIFACT_ID","PINNED_V1_8_ARTIFACT_DIGEST_SHA256","PINNED_V1_8_REGISTRY_FILE_SHA256","PINNED_V1_8_EVENT_SET_FILE_SHA256","PINNED_V1_8_EXPORT_MANIFEST_SHA256"]:
            with self.subTest(name=name):self.assertIn('"'+name+'"',self.source)
    def test_no_historical_run_or_sha_literal(self):
        self.assertNotIn("36932258437",self.source)
        self.assertNotIn("ef24423cb469b4d7922bd0407f2b681a8ff7ee8d4d8988667ba9604e05ebd028",self.source)
    def test_flat_zip_names(self):
        self.assertIn('chr(92) not in item.filename',self.source)
        self.assertIn('"/" not in item.filename',self.source)

if __name__=="__main__":unittest.main()
