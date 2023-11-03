from bookmark.models import Bookmark
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

class Command(BaseCommand):
    help = _(u"Looks for redirected bookmarks")

    def handle(self, *args, **options):
        redirected = Bookmark.objects.filter(link_check_result="redirect")
        count = redirected.count()
        for idx, r in enumerate(redirected):

            print(r)
            print(r.url)
            print("%d/%d - %s%s" % (idx+1, count, "http://localhost:9030", reverse("bookmark:edit", args=[r.id,])))
            print("%s%s" % ("http://localhost:9030", reverse("admin:bookmark_bookmark_change", args=[r.id,])))
            print("-------------------")