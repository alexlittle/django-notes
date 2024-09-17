from django.contrib import admin
from notes.models import Note, Tag, NoteTag


class NoteTagInline(admin.TabularInline):
    model = NoteTag
    extra = 1


class NoteAdmin(admin.ModelAdmin):
    list_display = ('url', 'title', 'link_check_date', 'link_check_result')
    search_fields = ['url',
                     'title',
                     'description',
                     'link_check_date',
                     'link_check_result']
    inlines = [
        NoteTagInline
    ]


class TagAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'slug',
                    'favourite',
                    'count')
    search_fields = ['name', 'slug']
    ordering = ('-favourite', 'name',)

    def count(self, obj):
        return obj.note_count()

    count.short_description = "Note count"


class NoteTagAdmin(admin.ModelAdmin):
    list_display = ('note', 'tag')


admin.site.register(Note, NoteAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(NoteTag, NoteTagAdmin)
