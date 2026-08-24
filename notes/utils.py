import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Count, Q
from django.utils import timezone


def get_user_aware_date(user):
    return get_user_aware_datetime(user).date()


def get_user_aware_datetime(user):
    """
    Returns a datetime.datetime.now() object that is aware of the user's timezone.

    Args:
        user: A Django user object.

    Returns:
        datetime: A datetime.datetime object in the user's timezone, falling back
        to Django's current timezone if the user has no valid timezone set.
    """
    if not user.is_authenticated:
        return timezone.now()

    try:
        user_timezone = user.profile.timezone
        if isinstance(user_timezone, str):
            user_timezone = ZoneInfo(user_timezone)
        return datetime.datetime.now(user_timezone)
    except (AttributeError, TypeError, ValueError, ZoneInfoNotFoundError):
        return timezone.now()


def is_showall(request):
    showall_str = request.GET.get("showall", "false").lower()
    return showall_str != "false"


def get_filtered_notes(user, filter):
    from notes.models import Note

    slug_list = filter.split("+")
    return (
        Note.objects.filter(user=user, notetag__tag__slug__in=slug_list)
        .exclude(status="completed")
        .annotate(
            matched_tags=Count(
                "notetag__tag", filter=Q(notetag__tag__slug__in=slug_list), distinct=True
            )
        )
        .filter(matched_tags=len(slug_list))
    )
