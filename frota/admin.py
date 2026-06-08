from django.contrib import admin
from .models import Abastecimento, Manutencao, Motorista, Veiculo, Viagem


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ['placa', 'marca', 'modelo', 'ano', 'km_atual', 'status', 'empresa']
    list_filter  = ['status', 'empresa']
    search_fields = ['placa', 'modelo', 'marca']


@admin.register(Abastecimento)
class AbastecimentoAdmin(admin.ModelAdmin):
    list_display = ['veiculo', 'data', 'litros', 'valor_total', 'posto']
    list_filter  = ['veiculo__empresa', 'data']


@admin.register(Manutencao)
class ManutencaoAdmin(admin.ModelAdmin):
    list_display = ['veiculo', 'tipo', 'data', 'valor', 'oficina']
    list_filter  = ['tipo', 'veiculo__empresa']


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'cpf', 'cnh_categoria', 'cnh_validade', 'status', 'empresa']
    list_filter  = ['status', 'empresa']


@admin.register(Viagem)
class ViagemAdmin(admin.ModelAdmin):
    list_display = ['veiculo', 'origem', 'destino', 'saida', 'status', 'motorista']
    list_filter  = ['status', 'veiculo__empresa']
