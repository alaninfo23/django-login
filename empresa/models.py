from django.conf import settings
from django.db import models


class Empresa(models.Model):
    nome        = models.CharField(max_length=200)
    slug        = models.SlugField(max_length=60, unique=True)
    criada_em   = models.DateTimeField(auto_now_add=True)
    ativa       = models.BooleanField(default=True)
    logo        = models.ImageField(upload_to='logos/', blank=True, null=True)

    def __str__(self):
        return self.nome


class MembroEmpresa(models.Model):
    class Perfil(models.TextChoices):
        ADMIN    = 'admin',    'Administrador'
        OPERADOR = 'operador', 'Operador'

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='membros')
    user    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='membros')
    perfil  = models.CharField(max_length=10, choices=Perfil.choices, default=Perfil.OPERADOR)
    ativo   = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [['empresa', 'user']]

    def __str__(self):
        return f'{self.user.username} @ {self.empresa.nome} ({self.get_perfil_display()})'
