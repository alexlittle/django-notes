from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

class ChatLog(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    create_date = models.DateTimeField(default=timezone.now)
    query = models.TextField(blank=False, null=False, default=None)
    response = models.TextField(blank=False, null=False, default=None)

    class Meta:
        verbose_name = _('Chat Log')
        verbose_name_plural = _('Chat Logs')

    def __str__(self):
        return self.query