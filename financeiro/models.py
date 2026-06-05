from django.conf import settings
from django.db import models
from empresa.models import Empresa


class CentroCusto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='centros_custo', null=True)
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='centros_custo')
    nome    = models.CharField(max_length=200)

    class Meta:
        ordering = ['nome']
        unique_together = [['empresa', 'nome']]

    def __str__(self):
        return self.nome


class SubGrupo(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='subgrupos', null=True)
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subgrupos')
    nome    = models.CharField(max_length=200)

    class Meta:
        ordering = ['nome']
        unique_together = [['empresa', 'nome']]

    def __str__(self):
        return self.nome


class FormaPagamento(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='formas_pagamento', null=True)
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='formas_pagamento')
    nome    = models.CharField(max_length=200)

    class Meta:
        ordering = ['nome']
        unique_together = [['empresa', 'nome']]

    def __str__(self):
        return self.nome


class Despesa(models.Model):
    class Situacao(models.TextChoices):
        PAGO     = 'pago',     'Pago'
        PENDENTE = 'pendente', 'Pendente'

    empresa         = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='despesas', null=True)
    user            = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='despesas')
    data            = models.DateField()
    centro_custo    = models.CharField(max_length=200, verbose_name='Centro de Custo')
    subgrupo        = models.CharField(max_length=200, verbose_name='SubGrupo')
    descricao       = models.CharField(max_length=500, verbose_name='Descrição')
    valor           = models.DecimalField(max_digits=14, decimal_places=2)
    forma_pagamento = models.CharField(max_length=200, verbose_name='Forma de Pagamento')
    situacao        = models.CharField(max_length=10, choices=Situacao.choices, default=Situacao.PENDENTE)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-created_at']

    def __str__(self):
        return f'{self.descricao} — R${self.valor} ({self.get_situacao_display()})'


class Repasse(models.Model):
    class Tipo(models.TextChoices):
        APORTE  = 'aporte',  'Aporte'
        REPASSE = 'repasse', 'Repasse'

    empresa    = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='repasses', null=True)
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='repasses')
    data       = models.DateField()
    origem     = models.CharField(max_length=200, verbose_name='Centro de Origem')
    destino    = models.CharField(max_length=200, verbose_name='Centro de Destino')
    valor      = models.DecimalField(max_digits=14, decimal_places=2)
    tipo       = models.CharField(max_length=10, choices=Tipo.choices)
    descricao  = models.TextField(blank=True, verbose_name='Descrição')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-created_at']

    def __str__(self):
        return f'{self.get_tipo_display()} {self.origem}→{self.destino} R${self.valor}'
