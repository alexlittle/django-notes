from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.views import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('bookmark.urls')),
]

'''
if settings.DEBUG:
    urlpatterns += [
        path('media/<str:path>',
            static.serve,
            {'document_root': settings.MEDIA_ROOT}),
        path('static/<str:path>',
            static.serve,
            {'document_root': settings.STATIC_ROOT})]
'''