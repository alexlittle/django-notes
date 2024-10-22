
import datetime
import xml.dom.minidom

from django.core.management.base import BaseCommand

from notes.models import Note, NoteTag, Tag


class Command(BaseCommand):
    help = 'Import html file'

    def add_arguments(self, parser):
        parser.add_argument('importfile', type=str)

    def handle(self, *args, **options):
        import_file = options['importfile']
        self.stdout.write(options['importfile'])

        doc = xml.dom.minidom.parse(import_file)

        bookmarks = doc.getElementsByTagName('a')
        for bookmark_element in bookmarks:
            url = bookmark_element.getAttribute('href')
            title = bookmark_element.firstChild.nodeValue
            import_tags = bookmark_element.getAttribute('tags')
            date = bookmark_element.getAttribute('add_date')

            bookmark, created = Note.objects.get_or_create(url=url)
            if created:
                bookmark.url = url
                bookmark.title = title
                bookmark.create_date = \
                    datetime.datetime \
                    .fromtimestamp(int(date)) \
                    .strftime('%Y-%m-%d %H:%M:%S')
                bookmark.save()

                tags = [x.strip() for x in import_tags.split(',')]
                for t in tags:
                    tag, created = Tag.objects.get_or_create(name=t)
                    bookmark_tag, created = NoteTag.objects \
                        .get_or_create(bookmark=bookmark, tag=tag)

                self.stdout.write(bookmark.url + ": added")
