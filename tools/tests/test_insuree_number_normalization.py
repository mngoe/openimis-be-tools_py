from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase

from tools.services import get_or_create_family_from_xml, get_or_create_insuree_from_xml


class InsureeXmlNormalizationTest(TestCase):
    @mock.patch("tools.services.Insuree.objects.get_or_create")
    def test_insuree_xml_trims_chf_id(self, mock_get_or_create):
        mock_get_or_create.return_value = (mock.Mock(), True)

        get_or_create_insuree_from_xml({"CHFID": "120902348063480 ", "LastName": "X"}, 1)

        kwargs = mock_get_or_create.call_args.kwargs
        self.assertEqual(kwargs["chf_id"], "120902348063480")
        self.assertEqual(kwargs["defaults"]["chf_id"], "120902348063480")

    @mock.patch("tools.services.Insuree.objects.get_or_create")
    def test_insuree_xml_rejects_invisible_character(self, mock_get_or_create):
        with self.assertRaises(ValidationError):
            get_or_create_insuree_from_xml({"CHFID": "1209\t02348063480"}, 1)

        mock_get_or_create.assert_not_called()

    @mock.patch("tools.services.Family.objects.get_or_create")
    @mock.patch("tools.services.Insuree.objects.get")
    def test_family_xml_normalizes_hof_chf_id(self, mock_insuree_get, mock_family_get_or_create):
        mock_insuree_get.return_value = mock.Mock(id=42)
        mock_family_get_or_create.return_value = (mock.Mock(), True)

        get_or_create_family_from_xml({"CHFID": "001", "HOFCHFID": "120902348063480 "}, 1)

        self.assertEqual(
            mock_insuree_get.call_args.kwargs["chf_id"],
            "120902348063480",
        )
