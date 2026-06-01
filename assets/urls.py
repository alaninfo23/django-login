from django.urls import path
from . import views

urlpatterns = [
    path('',              views.asset_list,   name='asset_list'),
    path('novo/',         views.asset_create, name='asset_create'),
    path('<int:pk>/editar/',  views.asset_edit,   name='asset_edit'),
    path('<int:pk>/deletar/', views.asset_delete, name='asset_delete'),
    path('dashboard/',    views.dashboard,    name='dashboard'),
]
