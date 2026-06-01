from django.conf import settings
from django.db import models


class Asset(models.Model):

    class AssetType(models.TextChoices):
        CAR       = 'carro',    'Carro'
        MOTO      = 'moto',     'Moto'
        TRUCK     = 'caminhao', 'Caminhão'
        PROPERTY  = 'imovel',   'Imóvel'
        MACHINE   = 'maquina',  'Máquina'
        OTHER     = 'outro',    'Outro'

    class Status(models.TextChoices):
        ACTIVE  = 'ativo',    'Ativo'
        SOLD    = 'vendido',  'Vendido'
        BROKEN  = 'quebrado', 'Quebrado'

    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assets')
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
