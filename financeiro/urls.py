from django.urls import path
from . import views

urlpatterns = [
    path('cadastros/',               views.cadastros,                  name='cadastros'),
    path('dashboard/',               views.financeiro_dashboard,        name='financeiro_dashboard'),
    path('relatorios/',              views.relatorios,                  name='relatorios'),
    path('relatorios/despesas-centro/pdf/',    views.rel_despesas_centro_pdf,   name='rel_despesas_centro_pdf'),
    path('relatorios/despesas-centro/excel/',  views.rel_despesas_centro_excel, name='rel_despesas_centro_excel'),
    path('relatorios/despesas-subgrupo/pdf/',  views.rel_despesas_subgrupo_pdf, name='rel_despesas_subgrupo_pdf'),
    path('relatorios/despesas-subgrupo/excel/',views.rel_despesas_subgrupo_excel,name='rel_despesas_subgrupo_excel'),
    path('relatorios/repasses/pdf/',           views.rel_repasses_pdf,          name='rel_repasses_pdf'),
    path('relatorios/repasses/excel/',         views.rel_repasses_excel,        name='rel_repasses_excel'),
    path('relatorios/completo/pdf/',           views.rel_completo_pdf,          name='rel_completo_pdf'),
    path('despesas/',                    views.despesa_list,   name='despesa_list'),
    path('despesas/nova/',               views.despesa_create, name='despesa_create'),
    path('despesas/<int:pk>/editar/',    views.despesa_edit,   name='despesa_edit'),
    path('despesas/<int:pk>/deletar/',   views.despesa_delete, name='despesa_delete'),
    path('repasses/',                    views.repasse_list,   name='repasse_list'),
    path('repasses/novo/',               views.repasse_create, name='repasse_create'),
    path('repasses/<int:pk>/editar/',    views.repasse_edit,   name='repasse_edit'),
    path('repasses/<int:pk>/deletar/',   views.repasse_delete, name='repasse_delete'),
]
