"""
Security parity tests for the tools module (registers / extracts / uploads REST API)
against the openimis-dev-tools reference (release/26.10).

Each test asserts the REFERENCE behaviour: a failure is a gap in Cameroon.
Tags: [REF <reference file>::<test or line>] ported, [NEW] no reference equivalent.

The services behind the views are replaced by a sentinel that raises `_Reached`: the
tests only judge the access gate (rights + scope), never the file generation.

Run: python manage.py test tools.tests.test_security_parity --keepdb
"""
from unittest import mock
from xml.etree import ElementTree

from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Officer
from core.test_helpers import create_right_only_user, create_security_tree, get_test_token

# reference rights (openimis-dev-tools tools/apps.py DJANGO_PERMS)
REGISTER_ANY = 131000
REGISTER_RIGHTS = {  # path -> query right
    "registers/download_diagnoses": 131001,
    "registers/download_healthfacilities": 131003,
    "registers/download_locations": 131005,
    "registers/download_items": 131007,
    "registers/download_services": 131009,
}
REGISTER_UPLOADS = [
    "registers/upload_diagnoses", "registers/upload_healthfacilities",
    "registers/upload_locations", "registers/upload_items", "registers/upload_services",
]
MASTER_DATA = 131101
PHONE_EXTRACT = 131103
CLAIMS_UPLOAD = 131104
RENEWALS_EXTRACT = 131105
FEEDBACKS_EXTRACT = 131106
EXTRACT_RIGHTS = [MASTER_DATA, PHONE_EXTRACT, CLAIMS_UPLOAD, RENEWALS_EXTRACT, FEEDBACKS_EXTRACT]


class _Reached(Exception):
    """The request went past the access gate into the service."""


def _url(path):
    return f"/{settings.SITE_ROOT()}tools/{path}"


class _Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tree = create_security_tree("SPT")
        cls.no_right = create_right_only_user("spt_noright", [], [cls.tree.d1.id])
        cls.extract_user = create_right_only_user(
            "spt_extract", EXTRACT_RIGHTS, [cls.tree.d1.id])
        cls.officer2 = Officer.objects.create(
            code="SPTOFF2", last_name="Officer", other_names="Two", location=cls.tree.d2,
            audit_user_id=-1, validity_from="2019-01-01")

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def client_for(self, user=None):
        client = APIClient(raise_request_exception=True)
        if user is not None:
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {get_test_token(user)}")
        return client

    def assertRefused(self, call, msg=""):
        """The response is 401/403/404 and the service was never reached."""
        try:
            response = call()
        except _Reached:
            self.fail(f"access gate let the request through to the service {msg}")
        self.assertIn(response.status_code, (401, 403, 404), f"{msg} -> {response.status_code}")


class RegisterRightsTest(_Base):

    def test_register_downloads_allowed_and_denied(self):
        """[REF tools/tests/test_rights_roles.py::RegisterRightsTests::test_register_downloads_allowed_and_denied]
        Reference: has_perms is OR over the configured list, the query right alone opens the
        download. Cameroon User.has_perms (core/models/user.py) is Django's AND."""
        for path, right in REGISTER_RIGHTS.items():
            with self.subTest(path=path):
                allowed = create_right_only_user(f"spt_r{right}", [right], [self.tree.d1.id])
                response = self.client_for(allowed).get(_url(path))
                self.assertEqual(200, response.status_code, f"{path} with right {right}")
                response_no = self.client_for(self.no_right).get(_url(path))
                self.assertIn(response_no.status_code, (401, 403), path)

    def test_register_downloads_refuse_anonymous(self):
        """[REF tools/views.py checkUserWithRights = IsAuthenticated + rights]"""
        for path in REGISTER_RIGHTS:
            with self.subTest(path=path):
                response = self.client_for(None).get(_url(path))
                self.assertIn(response.status_code, (401, 403), path)

    def test_register_uploads_refused_without_right(self):
        """[REF tools/views.py upload_* checkUserWithRights(registers_*_perms)]"""
        for path in REGISTER_UPLOADS:
            with self.subTest(path=path):
                response = self.client_for(self.no_right).post(_url(path), {})
                self.assertIn(response.status_code, (401, 403), path)


@mock.patch("tools.views.services.create_master_data_export", side_effect=_Reached)
@mock.patch("tools.views.services.create_phone_extract", side_effect=_Reached)
@mock.patch("tools.views.services.create_officer_feedbacks_export", side_effect=_Reached)
@mock.patch("tools.views.services.create_officer_renewals_export", side_effect=_Reached)
class ExtractRightsTest(_Base):
    """Cameroon tools/apps.py:13-17 ships `extracts_*_perms: []` - has_perms([]) is True,
    so every authenticated user holds them. Reference: 131101..131106."""

    def test_master_data_extract_requires_its_right(self, *_):
        """[REF tools/apps.py DJANGO_PERMS masterDataExtract.query 131101]"""
        self.assertRefused(lambda: self.client_for(self.no_right).get(
            _url("extracts/download_master_data")), "master data")

    def test_phone_extract_requires_its_right(self, *_):
        """[REF tools/apps.py DJANGO_PERMS phoneExtract.query 131103]"""
        self.assertRefused(lambda: self.client_for(self.no_right).get(
            _url("extracts/download_phone_extract"), {"location": self.tree.d1.id}),
            "phone extract")

    def test_feedbacks_extract_requires_its_right(self, *_):
        """[REF tools/apps.py DJANGO_PERMS officerFeedbacksExtract.query 131106]"""
        self.assertRefused(lambda: self.client_for(self.no_right).get(
            _url("extracts/download_feedbacks"), {"officer_id": self.officer2.id}),
            "feedbacks")

    def test_renewals_extract_requires_its_right(self, *_):
        """[REF tools/apps.py DJANGO_PERMS officerRenewalsExtract.query 131105]"""
        self.assertRefused(lambda: self.client_for(self.no_right).get(
            _url("extracts/download_renewals"), {"officer_id": self.officer2.id}),
            "renewals")

    def test_extracts_refuse_anonymous(self, *_):
        """[REF tools/views.py extracts: has_perms on a non-empty right list]"""
        for path, params in (("extracts/download_master_data", {}),
                             ("extracts/download_phone_extract", {"location": self.tree.d1.id}),
                             ("extracts/download_feedbacks", {"officer_id": self.officer2.id}),
                             ("extracts/download_renewals", {"officer_id": self.officer2.id})):
            with self.subTest(path=path):
                self.assertRefused(lambda: self.client_for(None).get(_url(path), params), path)


@mock.patch("tools.views.services.open_claim_archive", side_effect=_Reached)
class ClaimUploadRightsTest(_Base):
    """`upload_claims` is a plain Django view (`@require_http_methods`), not a DRF one:
    the Bearer token is not read and `extracts_upload_claims_perms` is []."""

    def _post(self, user):
        archive = SimpleUploadedFile("claims.zip", b"PK\x05\x06" + b"\x00" * 18,
                                     content_type="application/zip")
        return self.client_for(user).post(_url("extracts/upload_claims"), {"file": archive})

    # the view swallows every exception of the service into a 400, so "reached" is read
    # from the mock rather than from the sentinel

    def test_claim_upload_refuses_anonymous(self, _open):
        """[REF tools/apps.py DJANGO_PERMS claimsUpload.create 131104]"""
        response = self._post(None)
        self.assertFalse(_open.called, "anonymous request reached open_claim_archive")
        self.assertIn(response.status_code, (401, 403), response.status_code)

    def test_claim_upload_requires_its_right(self, _open):
        """[REF tools/apps.py DJANGO_PERMS claimsUpload.create 131104]"""
        response = self._post(self.no_right)
        self.assertFalse(_open.called, "request without right reached open_claim_archive")
        self.assertIn(response.status_code, (401, 403), response.status_code)


@mock.patch("tools.views.services.create_phone_extract", side_effect=_Reached)
@mock.patch("tools.views.services.create_officer_feedbacks_export", side_effect=_Reached)
@mock.patch("tools.views.services.create_officer_renewals_export", side_effect=_Reached)
class ExtractLocationScopeTest(_Base):
    """A user granted D1 (and holding the extract rights) must not extract D2 data."""

    def test_phone_extract_of_a_foreign_district_is_refused(self, *_):
        """[NEW] reference gap too: download_phone_extract does not check `location`
        against the user's districts (tools/views.py:402)."""
        self.assertRefused(lambda: self.client_for(self.extract_user).get(
            _url("extracts/download_phone_extract"), {"location": self.tree.d2.id}),
            "phone extract D2")

    def test_feedbacks_of_a_foreign_officer_are_refused(self, *_):
        """[NEW] get_object_or_404(Officer, id=...) is unscoped (tools/views.py:423)."""
        self.assertRefused(lambda: self.client_for(self.extract_user).get(
            _url("extracts/download_feedbacks"), {"officer_id": self.officer2.id}),
            "feedbacks officer D2")

    def test_renewals_of_a_foreign_officer_are_refused(self, *_):
        """[NEW] get_object_or_404(Officer, id=...) is unscoped (tools/views.py:443)."""
        self.assertRefused(lambda: self.client_for(self.extract_user).get(
            _url("extracts/download_renewals"), {"officer_id": self.officer2.id}),
            "renewals officer D2")

    def test_phone_extract_of_own_district_passes_the_gate(self, *_):
        """Positive control: the gate lets the D1 request through to the service."""
        with self.assertRaises(_Reached):
            self.client_for(self.extract_user).get(
                _url("extracts/download_phone_extract"), {"location": self.tree.d1.id})


@override_settings(ROW_SECURITY=True)
class ClaimUploadScopeTest(_Base):

    def test_upload_claim_for_a_foreign_health_facility_is_refused(self):
        """[REF tools/services.py upload_claim HF scope check
        (tools/tests/test_claim_upload.py)]"""
        from tools.services import InvalidXMLError, upload_claim

        xml = ElementTree.fromstring(
            f"<Claim><Details><HFCode>{self.tree.hf2.code}</HFCode></Details></Claim>")
        with self.assertRaises(InvalidXMLError):
            upload_claim(self.extract_user, xml)
