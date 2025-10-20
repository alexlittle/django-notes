from django.conf import settings

from notes.models import SavedFilter
from notes.utils import get_user_aware_datetime


def debug_mode(request):
    return {'DEBUG': settings.DEBUG}

def get_datetime(request):
    user = get_user_aware_datetime(request.user)
    return {'USER_TIME': user.strftime("%d %B %Y %H:%M:%S (%Z%z)") }


def favourites_processor(request):
    user = request.user

    if user.is_authenticated:
        favourites = SavedFilter.objects.all()
        return {'favourites': favourites}
    else:
        return {'favourites': None }

