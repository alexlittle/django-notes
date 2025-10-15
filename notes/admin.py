from django.contrib import admin
from notes.models import (Note,
                          Tag,
                          NoteTag,
                          NoteHistory,
                          NotesProfile,
                          SavedFilter,
                          TagSuggestion,
                          TagSuggestionInputTag,
                          NotesConfig)


class NoteTagInline(admin.TabularInline):
    model = NoteTag
    extra = 1


@admin.register(Note)
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


@admin.register(NotesProfile)
class NotesProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'timezone')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',
                    'slug',
                    'label',
                    'favourite',
                    'count')
    search_fields = ['name', 'slug']
    ordering = ('-favourite', 'name',)

    def count(self, obj):
        return obj.note_count()

    count.short_description = "Note count"


@admin.register(NoteTag)
class NoteTagAdmin(admin.ModelAdmin):
    list_display = ('note', 'tag')


@admin.register(NoteHistory)
class NoteHistoryAdmin(admin.ModelAdmin):
    list_display = ('note', 'update_date', 'action')


@admin.register(SavedFilter)
class SavedFilterAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'type', 'order_by')


@admin.register(TagSuggestion)
class TagSuggestionAdmin(admin.ModelAdmin):
    list_display = ('suggested_tag', 'confidence', 'lift', 'support')


@admin.register(TagSuggestionInputTag)
class TagSuggestionInputTagAdmin(admin.ModelAdmin):
    list_display = ('tag', 'suggestion')

@admin.register(NotesConfig)
class NotesConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'value')