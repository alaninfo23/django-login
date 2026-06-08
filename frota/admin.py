from django.contrib import admin
from .models import Abastecimento, Manutencao, Motorista, Veiculo, Viagem


def _empresa(request):
    return getattr(request, 'empresa', None)


class EmpresaAdminMixin:
    """Restringe o queryset à empresa do usuário logado (exceto superuser)."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        emp = _empresa(request)
        if emp is None:
            return qs.none()
        return qs.filter(**{self._empresa_lookup: emp})

    # cada subclasse define o caminho de FK até empresa
    _empresa_lookup = 'empresa'


@admin.register(Veiculo)
class VeiculoAdmin(EmpresaAdminMixin, admin.ModelAdmin):
    _empresa_lookup = 'empresa'
    list_display  = ['placa', 'marca', 'modelo', 'ano', 'km_atual', 'status', 'empresa']
    list_filter   = ['status', 'empresa']
    search_fields = ['placa', 'modelo', 'marca']


@admin.register(Motorista)
class MotoristaAdmin(EmpresaAdminMixin, admin.ModelAdmin):
    _empresa_lookup = 'empresa'
    list_display  = ['nome', 'cpf', 'cnh_categoria', 'cnh_validade', 'status', 'empresa']
    list_filter   = ['status', 'empresa']


@admin.register(Abastecimento)
class AbastecimentoAdmin(EmpresaAdminMixin, admin.ModelAdmin):
    _empresa_lookup = 'veiculo__empresa'
    list_display  = ['veiculo', 'data', 'litros', 'valor_total', 'posto']
    list_filter   = ['veiculo__empresa', 'data']


@admin.register(Manutencao)
class ManutencaoAdmin(EmpresaAdminMixin, admin.ModelAdmin):
    _empresa_lookup = 'veiculo__empresa'
    list_display  = ['veiculo', 'tipo', 'data', 'valor', 'oficina']
    list_filter   = ['tipo', 'veiculo__empresa']


@admin.register(Viagem)
class ViagemAdmin(EmpresaAdminMixin, admin.ModelAdmin):
    _empresa_lookup = 'veiculo__empresa'
    list_display  = ['veiculo', 'origem', 'destino', 'saida', 'status', 'motorista']
    list_filter   = ['status', 'veiculo__empresa']
