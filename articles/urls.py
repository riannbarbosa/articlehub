from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='articles-index'),
    path('<uuid:pk>/edit/', views.edit, name='articles-edit'),
    path('<uuid:pk>/delete/', views.delete, name='articles-delete'),
    path('bulk-delete/', views.bulk_delete, name='articles-bulk-delete'),
    path('lookup-doi/', views.lookup_doi, name='lookup-doi'),
]