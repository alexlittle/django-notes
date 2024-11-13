from django.contrib import admin
from assistant.models import ChatLog


class ChatLogAdmin(admin.ModelAdmin):
    list_display = ('create_date', 'query', 'response')


admin.site.register(ChatLog, ChatLogAdmin)