from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='ideas-index'),
    path('<uuid:pk>/edit/', views.edit, name='ideas-edit'),
    path('<uuid:pk>/delete/', views.delete, name='ideas-delete'),
    path('bulk-delete/', views.bulk_delete, name='ideas-bulk-delete'),
]
