from datetime import date, timedelta, datetime
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.text import slugify

from empresa.models import Empresa, MembroEmpresa
from frota.models import Abastecimento, Manutencao, Motorista, Veiculo, Viagem


# ── helpers ────────────────────────────────────────────────────────────────────

def make_user(username='user', password='senha123'):
    return User.objects.create_user(username=username, password=password)


def make_empresa(nome='Empresa Frota'):
    return Empresa.objects.create(nome=nome, slug=slugify(nome))


def make_membro(user, empresa, perfil='admin'):
    return MembroEmpresa.objects.create(empresa=empresa, user=user, perfil=perfil)


def make_veiculo(empresa, placa='ABC-1234', km_atual=0, status=Veiculo.Status.ATIVO):
    return Veiculo.objects.create(
        empresa=empresa, placa=placa, modelo='Gol', marca='VW',
        ano=2020, capacidade_carga='1.5', km_atual=km_atual, status=status,
    )


def make_motorista(empresa, nome='João Silva', cpf=None):
    return Motorista.objects.create(empresa=empresa, nome=nome, cpf=cpf)


def make_viagem(veiculo, motorista=None, km_inicial=1000, status=Viagem.Status.EM_ANDAMENTO, **kwargs):
    defaults = dict(
        origem='São Paulo', destino='Campinas',
        saida=datetime(2026, 6, 1, 8, 0),
        km_inicial=km_inicial, status=status,
    )
    defaults.update(kwargs)
    return Viagem.objects.create(veiculo=veiculo, motorista=motorista, **defaults)


def make_abastecimento(veiculo, km=500, litros='50.00', valor='250.00'):
    return Abastecimento.objects.create(
        veiculo=veiculo, data=date(2026, 6, 1),
        km_atual=km, litros=litros, valor_total=valor,
    )


def make_manutencao(veiculo, data=None, status=Manutencao.Status.REALIZADA, **kwargs):
    defaults = dict(
        tipo=Manutencao.Tipo.PREVENTIVA,
        descricao='Troca de óleo',
        status=status,
        data=data or date(2026, 6, 1),
    )
    defaults.update(kwargs)
    return Manutencao.objects.create(veiculo=veiculo, **defaults)


# ── Veiculo: atualizar_km ──────────────────────────────────────────────────────

class VeiculoAtualizarKmTests(TestCase):

    def setUp(self):
        self.empresa = make_empresa()
        self.veiculo = make_veiculo(self.empresa, km_atual=1000)

    def test_km_atualiza_quando_novo_e_maior(self):
        self.veiculo.atualizar_km(1500)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1500)

    def test_km_nao_reduz(self):
        self.veiculo.atualizar_km(500)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1000)

    def test_km_igual_nao_altera(self):
        self.veiculo.atualizar_km(1000)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1000)

    def test_km_none_nao_altera(self):
        self.veiculo.atualizar_km(None)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1000)

    def test_km_zero_nao_altera(self):
        self.veiculo.atualizar_km(0)
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1000)

    def test_km_como_string_funciona(self):
        """atualizar_km deve aceitar string numérica (vem do POST)."""
        self.veiculo.atualizar_km('2000')
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 2000)


# ── Veiculo: model ─────────────────────────────────────────────────────────────

class VeiculoModelTests(TestCase):

    def setUp(self):
        self.empresa = make_empresa()

    def test_str_contem_placa_marca_modelo(self):
        v = make_veiculo(self.empresa)
        self.assertIn('ABC-1234', str(v))
        self.assertIn('VW', str(v))

    def test_placa_unica_por_empresa(self):
        from django.db import IntegrityError
        make_veiculo(self.empresa, placa='XYZ-0001')
        with self.assertRaises(IntegrityError):
            make_veiculo(self.empresa, placa='XYZ-0001')

    def test_mesma_placa_em_empresas_diferentes(self):
        outra = make_empresa('Outra')
        make_veiculo(self.empresa, placa='XYZ-0001')
        v2 = make_veiculo(outra, placa='XYZ-0001')
        self.assertIsNotNone(v2.pk)

    def test_status_padrao_e_ativo(self):
        v = make_veiculo(self.empresa)
        self.assertEqual(v.status, Veiculo.Status.ATIVO)


# ── Abastecimento: model ───────────────────────────────────────────────────────

class AbastecimentoModelTests(TestCase):

    def setUp(self):
        self.empresa = make_empresa()
        self.veiculo = make_veiculo(self.empresa)

    def test_valor_por_litro_calculado(self):
        ab = make_abastecimento(self.veiculo, litros='50.00', valor='250.00')
        ab.litros = Decimal('50.00')
        ab.valor_total = Decimal('250.00')
        self.assertEqual(ab.valor_por_litro, Decimal('5.000'))

    def test_valor_por_litro_none_quando_litros_zero(self):
        ab = Abastecimento(veiculo=self.veiculo, data=date.today(),
                           km_atual=100, litros=0, valor_total='0')
        self.assertIsNone(ab.valor_por_litro)

    def test_str_contem_placa_e_litros(self):
        ab = make_abastecimento(self.veiculo)
        self.assertIn('ABC-1234', str(ab))

    def test_ordenacao_por_data_desc(self):
        make_abastecimento(self.veiculo, km=100)
        ab2 = Abastecimento.objects.create(
            veiculo=self.veiculo, data=date(2026, 7, 1),
            km_atual=200, litros='40', valor_total='200',
        )
        first = Abastecimento.objects.filter(veiculo=self.veiculo).first()
        self.assertEqual(first, ab2)


# ── Manutencao: properties ─────────────────────────────────────────────────────

class ManutencaoPropertiesTests(TestCase):

    def setUp(self):
        self.empresa = make_empresa()
        self.veiculo = make_veiculo(self.empresa)

    def test_vencida_quando_agendada_e_data_passada(self):
        man = make_manutencao(self.veiculo,
                              data=date.today() - timedelta(days=1),
                              status=Manutencao.Status.AGENDADA)
        self.assertTrue(man.vencida)

    def test_nao_vencida_quando_realizada(self):
        man = make_manutencao(self.veiculo,
                              data=date.today() - timedelta(days=1),
                              status=Manutencao.Status.REALIZADA)
        self.assertFalse(man.vencida)

    def test_vencendo_dentro_de_7_dias(self):
        man = make_manutencao(self.veiculo,
                              data=date.today() + timedelta(days=5),
                              status=Manutencao.Status.AGENDADA)
        self.assertTrue(man.vencendo)

    def test_nao_vencendo_alem_de_7_dias(self):
        man = make_manutencao(self.veiculo,
                              data=date.today() + timedelta(days=10),
                              status=Manutencao.Status.AGENDADA)
        self.assertFalse(man.vencendo)

    def test_vencendo_hoje(self):
        man = make_manutencao(self.veiculo,
                              data=date.today(),
                              status=Manutencao.Status.AGENDADA)
        self.assertTrue(man.vencendo)


# ── Motorista: properties ──────────────────────────────────────────────────────

class MotoristaPropertiesTests(TestCase):

    def setUp(self):
        self.empresa = make_empresa()

    def test_cnh_vencida_quando_data_passada(self):
        m = make_motorista(self.empresa)
        m.cnh_validade = date.today() - timedelta(days=1)
        self.assertTrue(m.cnh_vencida)

    def test_cnh_nao_vencida_quando_futura(self):
        m = make_motorista(self.empresa)
        m.cnh_validade = date.today() + timedelta(days=10)
        self.assertFalse(m.cnh_vencida)

    def test_cnh_vencida_false_sem_validade(self):
        m = make_motorista(self.empresa)
        m.cnh_validade = None
        self.assertFalse(m.cnh_vencida)

    def test_cnh_vencendo_dentro_de_30_dias(self):
        m = make_motorista(self.empresa)
        m.cnh_validade = date.today() + timedelta(days=20)
        self.assertTrue(m.cnh_vencendo)

    def test_cnh_nao_vencendo_alem_de_30_dias(self):
        m = make_motorista(self.empresa)
        m.cnh_validade = date.today() + timedelta(days=31)
        self.assertFalse(m.cnh_vencendo)

    def test_cnh_vencendo_false_sem_validade(self):
        m = make_motorista(self.empresa)
        m.cnh_validade = None
        self.assertFalse(m.cnh_vencendo)

    def test_dois_motoristas_sem_cpf_permitidos(self):
        """cpf=None não deve violar unique_together."""
        make_motorista(self.empresa, nome='Motorista A', cpf=None)
        m2 = make_motorista(self.empresa, nome='Motorista B', cpf=None)
        self.assertIsNotNone(m2.pk)

    def test_cpf_duplicado_na_mesma_empresa_bloqueado(self):
        from django.db import IntegrityError
        make_motorista(self.empresa, nome='João', cpf='111.111.111-11')
        with self.assertRaises(IntegrityError):
            make_motorista(self.empresa, nome='Pedro', cpf='111.111.111-11')


# ── Viagem: km_rodado property ─────────────────────────────────────────────────

class ViagemKmRodadoTests(TestCase):

    def setUp(self):
        self.empresa = make_empresa()
        self.veiculo = make_veiculo(self.empresa)

    def test_km_rodado_calculado(self):
        v = make_viagem(self.veiculo, km_inicial=1000, km_final=1300)
        self.assertEqual(v.km_rodado, 300)

    def test_km_rodado_none_sem_km_final(self):
        v = make_viagem(self.veiculo, km_inicial=1000)
        self.assertIsNone(v.km_rodado)

    def test_km_rodado_none_quando_final_menor(self):
        v = make_viagem(self.veiculo, km_inicial=1000, km_final=900)
        self.assertIsNone(v.km_rodado)


# ── Views: autenticação ────────────────────────────────────────────────────────

class FrotaAuthTests(TestCase):

    PROTECTED = [
        'frota_dashboard', 'frota_veiculos', 'frota_veiculo_create',
        'frota_abastecimentos', 'frota_manutencoes', 'frota_viagens', 'frota_motoristas',
    ]

    def test_views_redirecionam_sem_login(self):
        for name in self.PROTECTED:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302, msg=f'{name} deveria redirecionar')
            self.assertIn('/login', resp['Location'])


# ── fixture compartilhada ──────────────────────────────────────────────────────

class FrotaViewBase(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()
        make_membro(self.user, self.empresa)
        self.client.force_login(self.user)
        self.veiculo = make_veiculo(self.empresa, km_atual=1000)
        self.motorista = make_motorista(self.empresa)


# ── Views: veículos ────────────────────────────────────────────────────────────

class VeiculoViewTests(FrotaViewBase):

    def test_list_retorna_200(self):
        self.assertEqual(self.client.get(reverse('frota_veiculos')).status_code, 200)

    def test_list_exibe_apenas_veiculos_da_empresa(self):
        outra = make_empresa('Outra')
        make_veiculo(outra, placa='ZZZ-9999')
        resp = self.client.get(reverse('frota_veiculos'))
        self.assertContains(resp, 'ABC-1234')
        self.assertNotContains(resp, 'ZZZ-9999')

    def test_create_get_retorna_200(self):
        self.assertEqual(self.client.get(reverse('frota_veiculo_create')).status_code, 200)

    def test_create_post_cria_veiculo(self):
        self.client.post(reverse('frota_veiculo_create'), {
            'placa': 'NEW-0001', 'modelo': 'Corolla', 'marca': 'Toyota',
            'ano': 2023, 'capacidade_carga': '1.5', 'km_atual': 0, 'status': 'ativo',
        })
        self.assertTrue(Veiculo.objects.filter(placa='NEW-0001', empresa=self.empresa).exists())

    def test_create_post_redireciona(self):
        resp = self.client.post(reverse('frota_veiculo_create'), {
            'placa': 'NEW-0002', 'modelo': 'Uno', 'marca': 'Fiat',
            'ano': 2019, 'capacidade_carga': '0.5', 'km_atual': 0, 'status': 'ativo',
        })
        self.assertRedirects(resp, reverse('frota_veiculos'))

    def test_edit_atualiza_modelo(self):
        self.client.post(reverse('frota_veiculo_edit', args=[self.veiculo.pk]), {
            'placa': self.veiculo.placa, 'modelo': 'Gol Atualizado', 'marca': 'VW',
            'ano': 2020, 'capacidade_carga': '1.5', 'km_atual': 1000, 'status': 'ativo',
        })
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.modelo, 'Gol Atualizado')

    def test_delete_remove_veiculo_sem_registros(self):
        v = make_veiculo(self.empresa, placa='DEL-0001')
        self.client.post(reverse('frota_veiculo_delete', args=[v.pk]))
        self.assertFalse(Veiculo.objects.filter(pk=v.pk).exists())

    def test_delete_protegido_com_abastecimento(self):
        """Veículo com abastecimento não pode ser excluído."""
        make_abastecimento(self.veiculo)
        self.client.post(reverse('frota_veiculo_delete', args=[self.veiculo.pk]))
        self.assertTrue(Veiculo.objects.filter(pk=self.veiculo.pk).exists())

    def test_nao_acessa_veiculo_de_outra_empresa(self):
        outra = make_empresa('Outra')
        v = make_veiculo(outra, placa='OUT-0001')
        resp = self.client.get(reverse('frota_veiculo_edit', args=[v.pk]))
        self.assertEqual(resp.status_code, 404)


# ── Views: abastecimento ───────────────────────────────────────────────────────

class AbastecimentoViewTests(FrotaViewBase):

    def test_list_retorna_200(self):
        self.assertEqual(self.client.get(reverse('frota_abastecimentos')).status_code, 200)

    def test_create_post_cria_abastecimento(self):
        self.client.post(reverse('frota_abastecimento_create'), {
            'veiculo': self.veiculo.pk, 'data': '2026-06-01',
            'km_atual': 1200, 'litros': '50.00', 'valor_total': '300.00',
        })
        self.assertTrue(Abastecimento.objects.filter(veiculo=self.veiculo).exists())

    def test_create_atualiza_km_do_veiculo(self):
        """Criar abastecimento com km maior deve atualizar km do veículo."""
        self.client.post(reverse('frota_abastecimento_create'), {
            'veiculo': self.veiculo.pk, 'data': '2026-06-01',
            'km_atual': 1500, 'litros': '40.00', 'valor_total': '200.00',
        })
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1500)

    def test_create_nao_reduz_km_do_veiculo(self):
        """Abastecimento com km menor que o atual não deve reduzir km do veículo."""
        self.client.post(reverse('frota_abastecimento_create'), {
            'veiculo': self.veiculo.pk, 'data': '2026-06-01',
            'km_atual': 500, 'litros': '40.00', 'valor_total': '200.00',
        })
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1000)

    def test_delete_remove_abastecimento(self):
        ab = make_abastecimento(self.veiculo)
        self.client.post(reverse('frota_abastecimento_delete', args=[ab.pk]))
        self.assertFalse(Abastecimento.objects.filter(pk=ab.pk).exists())


# ── Views: manutenção ──────────────────────────────────────────────────────────

class ManutencaoViewTests(FrotaViewBase):

    def test_list_retorna_200(self):
        self.assertEqual(self.client.get(reverse('frota_manutencoes')).status_code, 200)

    def test_create_post_cria_manutencao(self):
        self.client.post(reverse('frota_manutencao_create'), {
            'veiculo': self.veiculo.pk, 'tipo': 'preventiva',
            'descricao': 'Troca de óleo', 'status': 'realizada',
            'data': '2026-06-01', 'km_manutencao': 1200,
        })
        self.assertTrue(Manutencao.objects.filter(veiculo=self.veiculo).exists())

    def test_create_com_km_atualiza_veiculo(self):
        self.client.post(reverse('frota_manutencao_create'), {
            'veiculo': self.veiculo.pk, 'tipo': 'revisao',
            'descricao': 'Revisão completa', 'status': 'realizada',
            'data': '2026-06-01', 'km_manutencao': 1800,
        })
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1800)

    def test_delete_remove_manutencao(self):
        man = make_manutencao(self.veiculo)
        self.client.post(reverse('frota_manutencao_delete', args=[man.pk]))
        self.assertFalse(Manutencao.objects.filter(pk=man.pk).exists())


# ── Views: viagem ──────────────────────────────────────────────────────────────

class ViagemViewTests(FrotaViewBase):

    def test_list_retorna_200(self):
        self.assertEqual(self.client.get(reverse('frota_viagens')).status_code, 200)

    def test_create_post_cria_viagem(self):
        self.client.post(reverse('frota_viagem_create'), {
            'veiculo': self.veiculo.pk, 'origem': 'SP', 'destino': 'RJ',
            'saida': '2026-06-01 08:00', 'km_inicial': 1000, 'status': 'em_andamento',
        })
        self.assertTrue(Viagem.objects.filter(veiculo=self.veiculo).exists())

    def test_create_veiculo_em_manutencao_bloqueado(self):
        """Veículo em manutenção não deve poder iniciar viagem."""
        v_man = make_veiculo(self.empresa, placa='MAN-0001', status=Veiculo.Status.MANUTENCAO)
        self.client.post(reverse('frota_viagem_create'), {
            'veiculo': v_man.pk, 'origem': 'SP', 'destino': 'RJ',
            'saida': '2026-06-01 08:00', 'km_inicial': 500, 'status': 'em_andamento',
        })
        self.assertFalse(Viagem.objects.filter(veiculo=v_man).exists())

    def test_encerrar_viagem_atualiza_km_e_status(self):
        """Encerrar viagem deve marcar como concluída e atualizar km do veículo."""
        viagem = make_viagem(self.veiculo, km_inicial=1000)
        self.client.post(reverse('frota_viagem_encerrar', args=[viagem.pk]), {
            'km_final': 1400, 'retorno': '2026-06-01 18:00',
        })
        viagem.refresh_from_db()
        self.veiculo.refresh_from_db()
        self.assertEqual(viagem.status, Viagem.Status.CONCLUIDA)
        self.assertEqual(viagem.km_final, 1400)
        self.assertEqual(self.veiculo.km_atual, 1400)

    def test_encerrar_viagem_km_menor_nao_encerra(self):
        """km_final menor que km_inicial não deve encerrar a viagem."""
        viagem = make_viagem(self.veiculo, km_inicial=1000)
        self.client.post(reverse('frota_viagem_encerrar', args=[viagem.pk]), {
            'km_final': 500,
        })
        viagem.refresh_from_db()
        self.assertEqual(viagem.status, Viagem.Status.EM_ANDAMENTO)

    def test_delete_remove_viagem(self):
        viagem = make_viagem(self.veiculo)
        self.client.post(reverse('frota_viagem_delete', args=[viagem.pk]))
        self.assertFalse(Viagem.objects.filter(pk=viagem.pk).exists())

    def test_viagem_concluida_via_create_atualiza_km(self):
        """Viagem criada já como concluída com km_final deve atualizar o veículo."""
        self.client.post(reverse('frota_viagem_create'), {
            'veiculo': self.veiculo.pk, 'origem': 'SP', 'destino': 'RJ',
            'saida': '2026-06-01 08:00', 'km_inicial': 1000,
            'km_final': 1300, 'status': 'concluida',
        })
        self.veiculo.refresh_from_db()
        self.assertEqual(self.veiculo.km_atual, 1300)

    def test_encerrar_viagem_ja_concluida_retorna_404(self):
        """Tentar encerrar viagem já concluída deve retornar 404."""
        viagem = make_viagem(self.veiculo, status=Viagem.Status.CONCLUIDA, km_final=1200)
        resp = self.client.post(reverse('frota_viagem_encerrar', args=[viagem.pk]), {
            'km_final': 1500,
        })
        self.assertEqual(resp.status_code, 404)


# ── Views: motorista ───────────────────────────────────────────────────────────

class MotoristaViewTests(FrotaViewBase):

    def test_list_retorna_200(self):
        self.assertEqual(self.client.get(reverse('frota_motoristas')).status_code, 200)

    def test_create_get_retorna_200(self):
        self.assertEqual(self.client.get(reverse('frota_motorista_create')).status_code, 200)

    def test_create_post_cria_motorista(self):
        self.client.post(reverse('frota_motorista_create'), {
            'nome': 'Carlos Santos', 'status': 'ativo',
        })
        self.assertTrue(Motorista.objects.filter(nome='Carlos Santos', empresa=self.empresa).exists())

    def test_create_sem_cpf_permite_multiplos(self):
        """Motoristas sem CPF não devem conflitar entre si."""
        antes = Motorista.objects.filter(empresa=self.empresa, cpf=None).count()
        self.client.post(reverse('frota_motorista_create'), {'nome': 'Sem CPF 1', 'status': 'ativo'})
        self.client.post(reverse('frota_motorista_create'), {'nome': 'Sem CPF 2', 'status': 'ativo'})
        self.assertEqual(Motorista.objects.filter(empresa=self.empresa, cpf=None).count(), antes + 2)

    def test_create_cpf_duplicado_exibe_erro(self):
        """CPF duplicado não deve criar segundo motorista."""
        Motorista.objects.create(empresa=self.empresa, nome='Existente', cpf='111.111.111-11')
        from django.db import transaction
        try:
            with transaction.atomic():
                self.client.post(reverse('frota_motorista_create'), {
                    'nome': 'Duplicado', 'cpf': '111.111.111-11', 'status': 'ativo',
                })
        except Exception:
            pass
        self.assertEqual(Motorista.objects.filter(cpf='111.111.111-11', empresa=self.empresa).count(), 1)

    def test_delete_remove_motorista(self):
        m = make_motorista(self.empresa, nome='Para Deletar', cpf='999.999.999-99')
        self.client.post(reverse('frota_motorista_delete', args=[m.pk]))
        self.assertFalse(Motorista.objects.filter(pk=m.pk).exists())

    def test_nao_acessa_motorista_de_outra_empresa(self):
        outra = make_empresa('Outra')
        m = make_motorista(outra, nome='Externo')
        resp = self.client.get(reverse('frota_motorista_edit', args=[m.pk]))
        self.assertEqual(resp.status_code, 404)
