from django.urls import path
from . import views

urlpatterns = [
    path('cadastros/',               views.cadastros,                  name='cadastros'),
    path('dashboard/',               views.financeiro_dashboard,        name='financeiro_dashboard'),
    path('despesas/',                    views.despesa_list,         name='despesa_list'),
    path('despesas/nova/',               views.despesa_create,       name='despesa_create'),
    path('despesas/bulk-delete/',        views.despesa_bulk_delete,  name='despesa_bulk_delete'),
    path('despesas/<int:pk>/editar/',    views.despesa_edit,         name='despesa_edit'),
    path('despesas/<int:pk>/deletar/',   views.despesa_delete,       name='despesa_delete'),
    path('repasses/',                    views.repasse_list,         name='repasse_list'),
    path('repasses/novo/',               views.repasse_create,       name='repasse_create'),
    path('repasses/bulk-delete/',        views.repasse_bulk_delete,  name='repasse_bulk_delete'),
    path('repasses/<int:pk>/editar/',    views.repasse_edit,         name='repasse_edit'),
    path('repasses/<int:pk>/deletar/',   views.repasse_delete,       name='repasse_delete'),
]
