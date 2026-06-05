from django.urls import path
from . import views

urlpatterns = [
    path('setup/',                        views.setup_empresa,             name='setup_empresa'),
    # Super-admin
    path('superadmin/',                   views.superadmin_empresas,       name='superadmin_empresas'),
    path('superadmin/criar/',             views.superadmin_empresa_criar,  name='superadmin_empresa_criar'),
    path('superadmin/<int:pk>/toggle/',   views.superadmin_empresa_toggle, name='superadmin_empresa_toggle'),
    # Gestão de usuários da empresa
    path('usuarios/',                     views.usuarios_list,    name='usuarios_list'),
    path('usuarios/convidar/',            views.usuario_convidar, name='usuario_convidar'),
    path('usuarios/<int:pk>/editar/',     views.usuario_editar,   name='usuario_editar'),
]
