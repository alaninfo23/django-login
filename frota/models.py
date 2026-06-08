from django.db import models
from empresa.models import Empresa


class Veiculo(models.Model):
    class Status(models.TextChoices):
        ATIVO       = 'ativo',       'Ativo'
        MANUTENCAO  = 'manutencao',  'Em Manutenção'
        INATIVO     = 'inativo',     'Inativo'

    empresa          = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='veiculos')
    placa            = models.CharField(max_length=10)
    modelo           = models.CharField(max_length=100)
    marca            = models.CharField(max_length=100)
    ano              = models.PositiveIntegerField()
    capacidade_carga = models.DecimalField(max_digits=8, decimal_places=2, help_text='Toneladas')
    km_atual         = models.PositiveIntegerField(default=0)
    status           = models.CharField(max_length=12, choices=Status.choices, default=Status.ATIVO)
    observacoes      = models.TextField(blank=True)
    criado_em        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['placa']
        unique_together = [['empresa', 'placa']]

    def __str__(self):
        return f'{self.placa} — {self.marca} {self.modelo} ({self.ano})'

    def atualizar_km(self, novo_km):
        """Atualiza km_atual apenas se novo_km for maior. Regra única para todo o módulo."""
        if novo_km and int(novo_km) > self.km_atual:
            self.km_atual = int(novo_km)
            self.save(update_fields=['km_atual'])


class Abastecimento(models.Model):
    veiculo     = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name='abastecimentos')
    data        = models.DateField()
    km_atual    = models.PositiveIntegerField()
    litros      = models.DecimalField(max_digits=8, decimal_places=2)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    posto       = models.CharField(max_length=200, blank=True)
    observacoes = models.TextField(blank=True)
    criado_em   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f'{self.veiculo.placa} — {self.data} — {self.litros}L'

    @property
    def valor_por_litro(self):
        if self.litros:
            return round(self.valor_total / self.litros, 3)
        return None


class Manutencao(models.Model):
    class Tipo(models.TextChoices):
        PREVENTIVA  = 'preventiva',  'Preventiva'
        CORRETIVA   = 'corretiva',   'Corretiva'
        REVISAO     = 'revisao',     'Revisão'
        PNEU        = 'pneu',        'Pneu'
        OUTRO       = 'outro',       'Outro'

    class Status(models.TextChoices):
        AGENDADA  = 'agendada',  'Agendada'
        REALIZADA = 'realizada', 'Realizada'

    veiculo          = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name='manutencoes')
    tipo             = models.CharField(max_length=12, choices=Tipo.choices)
    descricao        = models.CharField(max_length=500)
    status           = models.CharField(max_length=10, choices=Status.choices, default=Status.REALIZADA)
    oficina          = models.CharField(max_length=200, blank=True)
    valor            = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    km_manutencao    = models.PositiveIntegerField(null=True, blank=True)
    data             = models.DateField()
    proxima_revisao  = models.DateField(null=True, blank=True)
    criado_em        = models.DateTimeField(auto_now_add=True)

    @property
    def vencida(self):
        from datetime import date
        return self.status == self.Status.AGENDADA and self.data < date.today()

    @property
    def vencendo(self):
        """Agendada para os próximos 7 dias."""
        from datetime import date, timedelta
        hoje = date.today()
        return self.status == self.Status.AGENDADA and hoje <= self.data <= hoje + timedelta(days=7)

    class Meta:
        ordering = ['-data', '-criado_em']

    def __str__(self):
        return f'{self.veiculo.placa} — {self.get_tipo_display()} — {self.data}'


class Motorista(models.Model):
    class Status(models.TextChoices):
        ATIVO   = 'ativo',   'Ativo'
        INATIVO = 'inativo', 'Inativo'

    class CategoriaCNH(models.TextChoices):
        A  = 'A',  'A'
        B  = 'B',  'B'
        AB = 'AB', 'AB'
        C  = 'C',  'C'
        D  = 'D',  'D'
        E  = 'E',  'E'

    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='motoristas')
    nome           = models.CharField(max_length=200)
    cpf            = models.CharField(max_length=14, blank=True)
    telefone       = models.CharField(max_length=20, blank=True)
    cnh_numero     = models.CharField(max_length=20, blank=True, verbose_name='Número CNH')
    cnh_categoria  = models.CharField(max_length=2, choices=CategoriaCNH.choices, blank=True, verbose_name='Categoria CNH')
    cnh_validade   = models.DateField(null=True, blank=True, verbose_name='Validade CNH')
    status         = models.CharField(max_length=8, choices=Status.choices, default=Status.ATIVO)
    observacoes    = models.TextField(blank=True)
    criado_em      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        unique_together = [['empresa', 'cpf']]

    def __str__(self):
        return self.nome

    @property
    def cnh_vencida(self):
        from datetime import date
        return self.cnh_validade and self.cnh_validade < date.today()

    @property
    def cnh_vencendo(self):
        """Vence nos próximos 30 dias."""
        from datetime import date, timedelta
        if not self.cnh_validade:
            return False
        hoje = date.today()
        return hoje <= self.cnh_validade <= hoje + timedelta(days=30)


class Viagem(models.Model):
    class Status(models.TextChoices):
        EM_ANDAMENTO = 'em_andamento', 'Em Andamento'
        CONCLUIDA    = 'concluida',    'Concluída'
        CANCELADA    = 'cancelada',    'Cancelada'

    veiculo        = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name='viagens')
    motorista      = models.ForeignKey(Motorista, on_delete=models.SET_NULL, null=True, blank=True, related_name='viagens')
    origem         = models.CharField(max_length=200)
    destino        = models.CharField(max_length=200)
    saida          = models.DateTimeField()
    retorno        = models.DateTimeField(null=True, blank=True)
    km_inicial     = models.PositiveIntegerField()
    km_final       = models.PositiveIntegerField(null=True, blank=True)
    status         = models.CharField(max_length=12, choices=Status.choices, default=Status.EM_ANDAMENTO)
    ajudante1_nome      = models.CharField(max_length=200, blank=True, verbose_name='Ajudante 1 — Nome')
    ajudante1_telefone  = models.CharField(max_length=20,  blank=True, verbose_name='Ajudante 1 — Telefone')
    ajudante2_nome      = models.CharField(max_length=200, blank=True, verbose_name='Ajudante 2 — Nome')
    ajudante2_telefone  = models.CharField(max_length=20,  blank=True, verbose_name='Ajudante 2 — Telefone')
    ajudante3_nome      = models.CharField(max_length=200, blank=True, verbose_name='Ajudante 3 — Nome')
    ajudante3_telefone  = models.CharField(max_length=20,  blank=True, verbose_name='Ajudante 3 — Telefone')
    observacoes    = models.TextField(blank=True)
    criado_em      = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-saida']

    def __str__(self):
        return f'{self.veiculo.placa} | {self.origem} → {self.destino} ({self.saida:%d/%m/%Y})'

    @property
    def km_rodado(self):
        if self.km_final and self.km_final > self.km_inicial:
            return self.km_final - self.km_inicial
        return None
