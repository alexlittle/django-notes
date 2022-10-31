from django.conf import settings
from django.urls import include, path
from django.contrib import admin
from django.views import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('bookmark.urls')),
]
