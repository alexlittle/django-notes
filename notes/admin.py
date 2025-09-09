from django.contrib import admin
from notes.models import Note, Tag, NoteTag, NoteHistory, NotesProfile, SavedFilter


class NoteTagInline(admin.TabularInline):
    model = NoteTag
    extra = 1


class NoteAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'due_date', 'status', 'url', 'update_date')
    search_fields = ['url',
                     'title',
                     'description',
                     'status',
                     'priority']
    inlines = [
        NoteTagInline
    ]

class NotesProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'timezone')


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

class NoteHistoryAdmin(admin.ModelAdmin):
    list_display = ('note', 'update_date', 'action')

class SavedFilterAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'type')

admin.site.register(NotesProfile, NotesProfileAdmin)
admin.site.register(Note, NoteAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(NoteTag, NoteTagAdmin)
admin.site.register(NoteHistory, NoteHistoryAdmin)
admin.site.register(SavedFilter, SavedFilterAdmin)
