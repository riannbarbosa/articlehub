from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('verify/', views.verify_view, name='verify'),
    path('esqueci-senha/', views.forgot_password_view, name='forgot-password'),
    path('redefinir-senha/', views.reset_password_view, name='reset-password'),
    path('logout/', views.logout_view, name='logout'),
    path('grafo/', views.graph_view, name='graph'),
]
