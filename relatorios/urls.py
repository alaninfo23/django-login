from django.urls import path
from . import views

urlpatterns = [
    path('',                    views.central,           name='relatorios'),
    path('patrimonial/pdf/',    views.patrimonial_pdf,   name='rel_patrimonial_pdf'),
    path('patrimonial/excel/',  views.patrimonial_excel, name='rel_patrimonial_excel'),
    path('financeiro/pdf/',     views.financeiro_pdf,    name='rel_financeiro_pdf'),
    path('financeiro/excel/',   views.financeiro_excel,  name='rel_financeiro_excel'),
    path('frotas/pdf/',         views.frotas_pdf,        name='rel_frotas_pdf'),
    path('frotas/excel/',       views.frotas_excel,      name='rel_frotas_excel'),
]
