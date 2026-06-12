from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('artigos/', include('articles.urls')),
    path('', include('main.urls')),
]
