from django.contrib import admin

from bookmark.models import Bookmark, Tag, BookmarkTag


class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('url', 'title', 'link_check_date', 'link_check_result')
    search_fields = ['url',
                     'title',
                     'description',
                     'link_check_date',
                     'link_check_result']


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'favourite')
    search_fields = ['name', 'slug']


class BookmarkTagAdmin(admin.ModelAdmin):
    list_display = ('bookmark', 'tag')


admin.site.register(Bookmark, BookmarkAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(BookmarkTag, BookmarkTagAdmin)
