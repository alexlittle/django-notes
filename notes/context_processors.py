from django.conf import settings
from django.utils import timezone
from notes.utils import get_user_aware_datetime, get_user_aware_date


def debug_mode(request):
    return {'DEBUG': settings.DEBUG}

def get_datetime(request):
    user = get_user_aware_datetime(request.user)
    return {'USER_TIME': user.strftime("%d %B %Y %H:%M:%S (%Z%z)") }