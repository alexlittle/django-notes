import datetime
import pytz
from django.utils import timezone
from django.conf import settings

def get_user_aware_date(user):
    """
    Returns a datetime.datetime.now() object that is aware of the user's timezone.

    Args:
        user: A Django user object.

    Returns:
        A datetime.datetime object, or None if the user or timezone is invalid.
    """

    if not user.is_authenticated:
        return timezone.now().date()

    try:
        user_timezone = user.profile.timezone
        if isinstance(user_timezone, str):
            user_timezone = pytz.timezone(user_timezone)
        user_time = datetime.datetime.now(user_timezone)
        return user_time.date()

    except (AttributeError, pytz.exceptions.UnknownTimeZoneError):

        if settings.USE_TZ:
            return timezone.now().date()
        else:
            return datetime.datetime.now().date()

def get_user_aware_datetime(user):
    """
    Returns a datetime.datetime.now() object that is aware of the user's timezone.

    Args:
        user: A Django user object.

    Returns:
        A datetime.datetime object, or None if the user or timezone is invalid.
    """

    if not user.is_authenticated:
        return timezone.now()

    try:
        user_timezone = "Europe/Helsinki" #user.profile.timezone
        if isinstance(user_timezone, str):
            user_timezone = pytz.timezone(user_timezone)
        user_time = datetime.datetime.now(user_timezone)
        return user_time

    except (AttributeError, pytz.exceptions.UnknownTimeZoneError):
        if settings.USE_TZ:
            return timezone.now()
        else:
            return datetime.datetime.now()


def is_showall(request):
    showall_str = request.GET.get('showall', 'false').lower()
    if showall_str == 'false':
        return False
    else:
        return True