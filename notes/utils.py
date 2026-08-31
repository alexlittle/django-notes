import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Count, Q
from django.template.loader import render_to_string
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


def send_templated_mail(subject, template_name, context, recipient_list=None, from_email=None):
    """
    Render notes/emails/<template_name>.txt and .html and send them as a single
    multipart email, so every notification this system sends shares the same
    pair of easy-to-edit templates.

    Args:
        subject: Email subject line.
        template_name: Base name (without extension) of the .txt/.html pair
            under notes/templates/notes/emails/.
        context: Template context dict.
        recipient_list: Who to send to. Defaults to the addresses in
            settings.ADMINS.
        from_email: Sender address. Defaults to settings.DEFAULT_FROM_EMAIL.

    Returns:
        bool: True if an email was sent, False if there was nobody to send it to.
    """
    if recipient_list is None:
        recipient_list = [email for _name, email in settings.ADMINS]
    if not recipient_list:
        return False

    text_body = render_to_string(f"notes/emails/{template_name}.txt", context)
    html_body = render_to_string(f"notes/emails/{template_name}.html", context)

    email = EmailMultiAlternatives(str(subject), text_body, from_email, recipient_list)
    email.attach_alternative(html_body, "text/html")
    email.send()
    return True
