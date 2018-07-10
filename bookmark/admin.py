from django.contrib import admin

from bookmark.models import Bookmark, Tag, BookmarkTag

class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('url', 'title', 'description')
    search_fields = ['url','title', 'description']
  
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ['name', 'slug']  
    
class BookmarkTagAdmin(admin.ModelAdmin):
    list_display = ('bookmark', 'tag')  
    
admin.site.register(Bookmark, BookmarkAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(BookmarkTag, BookmarkTagAdmin)