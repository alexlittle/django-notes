'''
Removes unused tags
'''

from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from bookmark.models import Bookmark, BookmarkTag, Tag


class Command(BaseCommand):
    help = _(u"Checks the urls to ensure they are still valid links")
    errors = []

    def handle(self, *args, **options):
        tags = Tag.objects.filter(favourite=False).order_by('name')
        for tag in tags:
            if tag.bookmark_count() == 0:
                print(tag.name + ": deleted")
                tag.delete()

        for tag in tags:        
            if tag.bookmark_count() == 1:
                bookmark = Bookmark.objects.get(bookmarktag__tag=tag)
                print(tag.name + ": only 1 use : http://localhost.bookmark" 
                      + reverse('bookmark:edit', args=[bookmark.id]))