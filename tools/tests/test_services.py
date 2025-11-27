import os
from tablib import Dataset
from core.test_helpers import create_test_interactive_user
from django.test import TestCase
from tools.resources import ServiceResource
import importlib.resources


class ImportServiceTest(TestCase):
    
    def setUp(self) -> None:
        super(ImportServiceTest, self).setUp()
        self.user = create_test_interactive_user()

    def test_simple_import(self):
        resource = ServiceResource(self.user.id_for_audit)
        dataset = Dataset()

        with importlib.resources.open_text("tools.tests", "service_example.json") as f:
            dataset.load(f.read())
            result = resource.import_data(
                dataset, dry_run=True, use_transactions=True,
                collect_failed_rows=False,
            )
            self.assertEqual(result.has_errors(), False)

    def test_simple_export(self):
        result = ServiceResource(self.user.id_for_audit).export().dict
        self.assertTrue(result)
