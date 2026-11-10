from defusedxml.ElementTree import parse, ParseError
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


# Keep in sync with insuree.utils.normalize_insuree_number. Duplicated here so
# that the tools module has no runtime dependency on a given insuree version.
INSUREE_NUMBER_EDGE_CHARS = (
    " \t\n\r\f\v"
    "\u00a0\u2007\u202f\u200b\u200c\u200d\u2060\ufeff"
)
INSUREE_NUMBER_FORBIDDEN_CHARS = frozenset(
    "\t\n\r\f\v\u00a0\u2007\u202f\u200b\u200c\u200d\u2060\ufeff"
)


def normalize_insuree_number(value):
    """Trim and validate an insuree number read from an XML archive."""
    if value is None:
        return None
    normalized = str(value).strip(INSUREE_NUMBER_EDGE_CHARS)
    if any(char in INSUREE_NUMBER_FORBIDDEN_CHARS for char in normalized):
        raise ValidationError(_("Insuree number cannot contain invisible characters."))
    return normalized


def dictfetchall(cursor):
    """Return all rows from a cursor as a dict"""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def sanitize_xml(xml_file):
    return parse(xml_file)


def dmy_format_sql(vendor, field_name):
    if vendor == "postgresql":
        return """TO_CHAR({},'DD-MM-YYYY')""".format(field_name)
    else:
        return """CONVERT(NVARCHAR(10),{},103)""".format(field_name)
