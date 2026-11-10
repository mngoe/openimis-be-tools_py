"""
Location scope of the extract parameters.

The extracts take a location (phone extract) or an officer (feedbacks / renewals)
from the request. Neither the reference nor Cameroon compared them with the
user's districts, so a district user could extract any other district.
"""
from django.conf import settings


def _scoped_user(user):
    """The InteractiveUser to check, or None when no location check applies."""
    from core.models import InteractiveUser
    if not settings.ROW_SECURITY:
        return None
    i_user = getattr(user, "_u", user)
    if not isinstance(i_user, InteractiveUser) or i_user.is_imis_admin:
        return None
    return i_user


def _allowed_locations(i_user):
    from location.models import LocationManager
    # strict: a region only counts when every district of it is assigned
    return LocationManager().allowed(i_user.id, loc_types=["R", "D", "W", "V"], strict=True)


def location_in_scope(user, location_id):
    i_user = _scoped_user(user)
    if i_user is None:
        return True
    try:
        location_id = int(location_id)
    except (TypeError, ValueError):
        return False
    return _allowed_locations(i_user).filter(id=location_id).exists()


def officer_in_scope(user, officer):
    """The officer works inside the user's locations: by their own location or
    by one of the villages they are assigned to."""
    i_user = _scoped_user(user)
    if i_user is None:
        return True
    from location.models import OfficerVillage
    allowed = _allowed_locations(i_user)
    if officer.location_id and allowed.filter(id=officer.location_id).exists():
        return True
    return OfficerVillage.objects.filter(
        officer=officer, validity_to__isnull=True, location__in=allowed).exists()
