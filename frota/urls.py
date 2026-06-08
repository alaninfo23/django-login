from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',                   views.dashboard,             name='frota_dashboard'),
    # Veículos
    path('veiculos/',                    views.veiculo_list,          name='frota_veiculos'),
    path('veiculos/novo/',               views.veiculo_create,        name='frota_veiculo_create'),
    path('veiculos/<int:pk>/editar/',    views.veiculo_edit,          name='frota_veiculo_edit'),
    path('veiculos/<int:pk>/deletar/',   views.veiculo_delete,        name='frota_veiculo_delete'),
    path('veiculos/<int:pk>/detalhe/',   views.veiculo_detalhe,       name='frota_veiculo_detalhe'),
    # Abastecimentos
    path('abastecimentos/',              views.abastecimento_list,        name='frota_abastecimentos'),
    path('abastecimentos/novo/',         views.abastecimento_create,      name='frota_abastecimento_create'),
    path('abastecimentos/bulk-delete/',  views.abastecimentos_bulk_delete, name='frota_abastecimentos_bulk_delete'),
    path('abastecimentos/<int:pk>/editar/',  views.abastecimento_edit,    name='frota_abastecimento_edit'),
    path('abastecimentos/<int:pk>/deletar/', views.abastecimento_delete,  name='frota_abastecimento_delete'),
    # Manutenções
    path('manutencoes/',                 views.manutencao_list,           name='frota_manutencoes'),
    path('manutencoes/novo/',            views.manutencao_create,         name='frota_manutencao_create'),
    path('manutencoes/bulk-delete/',     views.manutencoes_bulk_delete,   name='frota_manutencoes_bulk_delete'),
    path('manutencoes/<int:pk>/editar/',  views.manutencao_edit,          name='frota_manutencao_edit'),
    path('manutencoes/<int:pk>/deletar/', views.manutencao_delete,        name='frota_manutencao_delete'),
    # Viagens
    path('viagens/',                     views.viagem_list,               name='frota_viagens'),
    path('viagens/novo/',                views.viagem_create,             name='frota_viagem_create'),
    path('viagens/bulk-delete/',         views.viagens_bulk_delete,       name='frota_viagens_bulk_delete'),
    path('viagens/<int:pk>/encerrar/',   views.viagem_encerrar,           name='frota_viagem_encerrar'),
    path('viagens/<int:pk>/editar/',     views.viagem_edit,               name='frota_viagem_edit'),
    path('viagens/<int:pk>/deletar/',    views.viagem_delete,             name='frota_viagem_delete'),
    # Motoristas
    path('motoristas/',                  views.motorista_list,        name='frota_motoristas'),
    path('motoristas/novo/',             views.motorista_create,      name='frota_motorista_create'),
    path('motoristas/<int:pk>/editar/',  views.motorista_edit,        name='frota_motorista_edit'),
    path('motoristas/<int:pk>/deletar/', views.motorista_delete,      name='frota_motorista_delete'),
]
