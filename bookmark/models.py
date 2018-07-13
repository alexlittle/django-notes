from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from bookmark.fields import AutoSlugField

class Tag (models.Model):
    create_date = models.DateTimeField(default=timezone.now)
    name = models.CharField(max_length=100, blank=False, null=False)
    slug = AutoSlugField(populate_from='name', max_length=100, blank=True, null=True)
    
    def __unicode__(self):
        return self.name

class Bookmark (models.Model):
    create_date = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    url = models.TextField(blank=False, null=False)
    title = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    tags = models.ManyToManyField(Tag, through='BookmarkTag', name='tags' )
    
    def __unicode__(self):
        if self.title:
            return self.title
        else:
            return self.url
        

    
class BookmarkTag(models.Model):
    bookmark = models.ForeignKey(Bookmark, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag,  on_delete=models.CASCADE)
 
    class Meta:
        verbose_name = _('Bookmark Tag')
        verbose_name_plural = _('Bookmark Tags')
        
    