from django.conf import settings
from django.db import models
from empresa.models import Empresa


class Asset(models.Model):

    class AssetType(models.TextChoices):
        CAR           = 'carro',           'Carro'
        MOTO          = 'moto',            'Moto'
        TRUCK         = 'caminhao',        'Caminhão'
        UTILITY       = 'utilitario',      'Veículo Utilitário'
        PROPERTY      = 'imovel',          'Imóvel'
        STORE         = 'loja',            'Loja / Ponto Comercial'
        MACHINE       = 'maquina',         'Máquina / Equipamento'
        IT            = 'ti',              'Equipamento de TI'
        FURNITURE     = 'moveis',          'Móveis / Utensílios'
        STOCK         = 'estoque',         'Estoque / Mercadoria'
        INVESTMENT    = 'investimento',    'Investimento (Banco/Aplicação)'
        PARTNERSHIP   = 'participacao',    'Participação Societária'
        OTHER         = 'outro',           'Outro'

    class Status(models.TextChoices):
        ACTIVE  = 'ativo',    'Ativo'
        SOLD    = 'vendido',  'Vendido'
        BROKEN  = 'quebrado', 'Quebrado'

    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assets')
    empresa          = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='assets', null=True)
    name             = models.CharField(max_length=200)
    asset_type       = models.CharField(max_length=20, choices=AssetType.choices)
    acquisition_value = models.DecimalField(max_digits=14, decimal_places=2)
    purchase_date    = models.DateField(null=True, blank=True)
    status           = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    location         = models.CharField(max_length=255, blank=True)
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_asset_type_display()}) — {self.user.username}'
