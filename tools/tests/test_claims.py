from unittest.mock import patch, PropertyMock

from django.test import TestCase
from unittest import mock

from tools.services import upload_claim, InvalidXMLError, get_xml_element, get_xml_element_int,\
    InvalidXmlInt, create_officer_feedbacks_export, create_officer_renewals_export
from xml.etree import ElementTree
from datetime import date, timedelta

from core.test_helpers import create_test_officer

from policy.services import insert_renewals
from claim.models import Claim, ClaimAdmin
from medical.models import Diagnosis 
from claim.services import create_feedback_prompt
from claim.test_helpers import (
    create_test_claim,
    create_test_claim_admin
)
from medical.test_helpers import (
    create_test_diagnosis,
    create_test_service, 
    create_test_item
)
from location.test_helpers import (
    create_test_health_facility,
    create_test_location,
)
from insuree.test_helpers import create_test_insuree
from program.test_helpers import create_test_program


class UploadClaimsTestCase(TestCase):
    def test_upload_claims_unknown_hf(self):
        with patch('tools.services.settings.ROW_SECURITY', new_callable=PropertyMock) as row_security_mock:
            row_security_mock.return_value = True
            mock_user = mock.Mock(is_anonymous=False)
            mock_user.has_perm = mock.MagicMock(return_value=True)
            mock_user.is_imis_admin = mock.MagicMock(return_value=False)
            with self.assertRaises(InvalidXMLError) as cm:
                upload_claim(
                    mock_user,
                    ElementTree.fromstring(
                        """
                               <Claim>
                                    <Details>
                                        <HFCode>WRONG</HFCode>
                                    </Details>
                                </Claim> 
                        """
                    ),
                )
            self.assertEqual(
                "User cannot upload claims for health facility WRONG",
                str(cm.exception),
            )


    def test_upload_claims_with_subservices(self):
        test_program = create_test_program(code="HIV1", name="HIV")
        with patch('tools.services.settings.ROW_SECURITY', new_callable=PropertyMock) as row_security_mock:
            row_security_mock.return_value = True
            mock_user = mock.Mock(is_anonymous=False)
            mock_user.has_perm = mock.MagicMock(return_value=True)
            mock_user.is_claim_admin = mock.MagicMock(return_value=True)
            mock_user.is_imis_admin = mock.MagicMock(return_value=False)
            location = create_test_location('D')
            insuree = create_test_insuree()
            hf = create_test_health_facility('HF1', location.id)
            item = create_test_item('D')
            service = create_test_service("A")
            subservice = create_test_service("A")
            subitem = create_test_item('D')
            diagnosis = create_test_diagnosis()
            claim_admin = create_test_claim_admin()
            claim_admin.refresh_from_db()

            claim_with_subservices_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
            <Claim>
                <Details>
                    <ClaimDate>2025-05-08</ClaimDate>
                    <HFCode>{hf.code}</HFCode>
                    <ClaimAdmin>{claim_admin.code}</ClaimAdmin>
                    <ClaimCode>Cl00124</ClaimCode>
                    <Program>HIV</Program>
                    <CHFID>{insuree.chf_id}</CHFID>
                    <StartDate>2024-06-03</StartDate>
                    <EndDate>2024-06-03</EndDate>
                    <ICDCode>{diagnosis.code}</ICDCode>
                    <VisitType>O</VisitType>
                    <ClaimPrefix>TEST</ClaimPrefix>
                </Details>
                <Items>
                    <Item>
                        <ItemCode>{item.code}</ItemCode>
                        <ItemQuantity>1</ItemQuantity>
                        <ItemPrice>1000.00</ItemPrice>
                    </Item>
                </Items>
                <Services>
                    <Service>
                        <ServiceCode>{service.code}</ServiceCode>
                        <ServiceQuantity>1</ServiceQuantity>
                        <ServicePrice>2000.00</ServicePrice>
                        <ServicePackageType>P</ServicePackageType>
                        <ServiceId>111</ServiceId>
                        <ServiceServiceSet>
                            <ServiceServiceSet>
                                <SubServiceCode>{subservice.code}</SubServiceCode>
                                <QtyAsked>1</QtyAsked>
                                <PriceAsked>500.00</PriceAsked>
                            </ServiceServiceSet>
                        </ServiceServiceSet>
                        <ServiceItemSet>
                            <ServiceItemSet>
                                <SubItemCode>{subitem.code}</SubItemCode>
                                <QtyAsked>1</QtyAsked>
                                <PriceAsked>1000.00</PriceAsked>
                            </ServiceItemSet>
                        </ServiceItemSet>
                    </Service>
                </Services>
            </Claim>
            """

            result = upload_claim(
                mock_user,
                ElementTree.fromstring(claim_with_subservices_xml),
            )

            self.assertTrue(result)


class GetXmlElement(TestCase):
    def test_get_xml_element(self):
        test_xml = ElementTree.fromstring(
            """
                <root>
                    <Exists>Exists</Exists>
                    <Int>123</Int>
                    <NotInt>123x</NotInt>
                    <Float>123.10</Float>
                    <NotFloat>123$10</NotFloat>
                </root>
            """
        )
        self.assertEqual("Exists", get_xml_element(test_xml, "Exists"))
        with self.assertRaises(AttributeError):
            get_xml_element(test_xml, "NotExists")
        self.assertEqual("DefaultValue", get_xml_element(test_xml, "NotExists", "DefaultValue"))

        self.assertEqual(123, get_xml_element_int(test_xml, "Int"))
        with self.assertRaises(AttributeError):
            get_xml_element_int(test_xml, "IntNotExists")
        self.assertEqual(456, get_xml_element_int(test_xml, "IntNotExists", 456))
        with self.assertRaises(InvalidXmlInt):
            get_xml_element_int(test_xml, "NotInt")
        with self.assertRaises(InvalidXmlInt):
            get_xml_element_int(test_xml, "NotInt", 456)


class register(TestCase):
    test_officer = None
    test_user = None
    claim = None
    @classmethod
    def setUpTestData(cls):
        
        cls.claim = create_test_claim(custom_props={'status': Claim.STATUS_CHECKED, 'feedback_status': Claim.FEEDBACK_SELECTED})
        
        cls.test_officer = create_test_officer(villages = [cls.claim.insuree.family.location])
        
        insert_renewals(
            date_from= date.today() + timedelta(days=-3650), 
            date_to=date.today()+ timedelta(days=7300), 
            officer_id=cls.test_officer.id, 
            reminding_interval=365, 
            location_id=cls.claim.insuree.family.location.id, 
            location_levels=4)
        
    def test_generating_feedback(self):
        class DummyUser:
            id_for_audit = -1
            id = 1
        mock_user = mock.Mock(is_anonymous=False)
        mock_user.has_perm = mock.MagicMock(return_value=True)
        mock_user.is_imis_admin = mock.MagicMock(return_value=False)
        
        create_feedback_prompt(self.claim, user=DummyUser())
        zip = create_officer_feedbacks_export(mock_user, self.test_officer)
        self.assertNotEqual(zip, None)
        
    def test_generating_renewal(self):
        mock_user = mock.Mock(is_anonymous=False)
        mock_user.has_perm = mock.MagicMock(return_value=True)
        mock_user.is_imis_admin = mock.MagicMock(return_value=False)
        zip = create_officer_renewals_export(mock_user, self.test_officer)
        self.assertNotEqual(zip, None)
    
    
    
