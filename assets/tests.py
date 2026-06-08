from datetime import date
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.text import slugify

from empresa.models import Empresa, MembroEmpresa
from assets.models import Asset


# ── helpers ────────────────────────────────────────────────────────────────────

def make_user(username='user', password='senha123'):
    return User.objects.create_user(username=username, password=password)


def make_empresa(nome='Empresa Teste'):
    return Empresa.objects.create(nome=nome, slug=slugify(nome))


def make_asset(user, empresa=None, **kwargs):
    defaults = dict(
        name='Notebook Dell',
        asset_type=Asset.AssetType.IT,
        acquisition_value=Decimal('4500.00'),
        status=Asset.Status.ACTIVE,
        empresa=empresa,
    )
    defaults.update(kwargs)
    return Asset.objects.create(user=user, **defaults)


# ── Model ──────────────────────────────────────────────────────────────────────

class AssetModelTests(TestCase):

    def setUp(self):
        self.user = make_user()

    def test_str_retorna_nome_tipo_e_usuario(self):
        asset = make_asset(self.user)
        self.assertIn('Notebook Dell', str(asset))
        self.assertIn(self.user.username, str(asset))

    def test_status_padrao_e_ativo(self):
        asset = make_asset(self.user)
        self.assertEqual(asset.status, Asset.Status.ACTIVE)

    def test_todos_os_tipos_validos(self):
        tipos = [t.value for t in Asset.AssetType]
        self.assertEqual(len(tipos), 13)

    def test_todos_os_status_validos(self):
        status = [s.value for s in Asset.Status]
        self.assertIn('ativo', status)
        self.assertIn('vendido', status)
        self.assertIn('quebrado', status)

    def test_ordenacao_padrao_por_created_at_desc(self):
        a1 = make_asset(self.user, name='Primeiro')
        a2 = make_asset(self.user, name='Segundo')
        assets = list(Asset.objects.filter(user=self.user))
        self.assertEqual(assets[0], a2)  # mais recente primeiro

    def test_empresa_pode_ser_nula(self):
        asset = make_asset(self.user, empresa=None)
        self.assertIsNone(asset.empresa)

    def test_purchase_date_pode_ser_nulo(self):
        asset = make_asset(self.user, purchase_date=None)
        self.assertIsNone(asset.purchase_date)


# ── Views: autenticação ────────────────────────────────────────────────────────

class AssetViewAuthTests(TestCase):

    PROTECTED_URLS = ['asset_list', 'asset_create', 'dashboard', 'home']

    def test_views_redirecionam_sem_login(self):
        for name in self.PROTECTED_URLS:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302, msg=f'{name} deveria redirecionar')
            self.assertIn('/login', resp['Location'])


# ── Views: asset_list ──────────────────────────────────────────────────────────

class AssetListViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse('asset_list')

    def test_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_exibe_apenas_assets_do_usuario(self):
        outro = make_user('outro')
        make_asset(self.user, name='Meu Bem')
        make_asset(outro, name='Bem do Outro')
        resp = self.client.get(self.url)
        self.assertContains(resp, 'Meu Bem')
        self.assertNotContains(resp, 'Bem do Outro')

    def test_filtro_por_nome(self):
        make_asset(self.user, name='Corolla')
        make_asset(self.user, name='Notebook')
        resp = self.client.get(self.url + '?q=corolla')
        self.assertContains(resp, 'Corolla')
        self.assertNotContains(resp, 'Notebook')

    def test_filtro_por_tipo(self):
        make_asset(self.user, name='Carro', asset_type=Asset.AssetType.CAR)
        make_asset(self.user, name='Note', asset_type=Asset.AssetType.IT)
        resp = self.client.get(self.url + '?asset_type=carro')
        self.assertContains(resp, 'Carro')
        self.assertNotContains(resp, 'Note')

    def test_filtro_por_status(self):
        make_asset(self.user, name='BemAtivo', status=Asset.Status.ACTIVE)
        make_asset(self.user, name='BemVendido', status=Asset.Status.SOLD)
        resp = self.client.get(self.url + '?status=vendido')
        self.assertContains(resp, 'BemVendido')
        self.assertNotContains(resp, 'BemAtivo')

    def test_order_invalido_nao_quebra(self):
        resp = self.client.get(self.url + '?order=injecao_sql')
        self.assertEqual(resp.status_code, 200)


# ── Views: asset_create ────────────────────────────────────────────────────────

class AssetCreateViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)
        self.url = reverse('asset_create')

    def test_get_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_cria_asset_e_redireciona(self):
        data = {
            'name': 'Monitor LG',
            'asset_type': 'ti',
            'acquisition_value': '1200.00',
            'status': 'ativo',
            'location': '',
            'notes': '',
        }
        resp = self.client.post(self.url, data)
        self.assertRedirects(resp, reverse('asset_list'))
        self.assertTrue(Asset.objects.filter(name='Monitor LG', user=self.user).exists())

    def test_asset_criado_pertence_ao_usuario_logado(self):
        self.client.post(self.url, {
            'name': 'Impressora', 'asset_type': 'maquina',
            'acquisition_value': '800.00', 'status': 'ativo',
        })
        asset = Asset.objects.get(name='Impressora')
        self.assertEqual(asset.user, self.user)


# ── Views: asset_edit / asset_delete ──────────────────────────────────────────

class AssetEditDeleteTests(TestCase):

    def setUp(self):
        self.user = make_user()
        empresa = make_empresa()
        MembroEmpresa.objects.create(empresa=empresa, user=self.user, perfil='admin')
        self.client.force_login(self.user)
        self.asset = make_asset(self.user)

    def test_edit_get_retorna_200(self):
        resp = self.client.get(reverse('asset_edit', args=[self.asset.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_edit_post_atualiza_nome(self):
        self.client.post(reverse('asset_edit', args=[self.asset.pk]), {
            'name': 'Notebook Atualizado', 'asset_type': 'ti',
            'acquisition_value': '4500.00', 'status': 'ativo',
        })
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.name, 'Notebook Atualizado')

    def test_delete_post_remove_asset(self):
        pk = self.asset.pk
        self.client.post(reverse('asset_delete', args=[pk]))
        self.assertFalse(Asset.objects.filter(pk=pk).exists())

    def test_nao_edita_asset_de_outro_usuario(self):
        outro = make_user('outro')
        asset_outro = make_asset(outro, name='Bem Alheio')
        resp = self.client.get(reverse('asset_edit', args=[asset_outro.pk]))
        self.assertEqual(resp.status_code, 404)


# ── Views: dashboard ──────────────────────────────────────────────────────────

class DashboardViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_retorna_200(self):
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)

    def test_dashboard_sem_assets_nao_quebra(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertContains(resp, '0')

    def test_dashboard_soma_patrimonio_corretamente(self):
        make_asset(self.user, acquisition_value=Decimal('1000.00'))
        make_asset(self.user, acquisition_value=Decimal('2500.00'))
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('patrimonio', resp.context)
        self.assertEqual(resp.context['patrimonio'], Decimal('3500.00'))

    def test_dashboard_nao_soma_assets_de_outro_usuario(self):
        outro = make_user('outro')
        make_asset(outro, acquisition_value=Decimal('99999.00'))
        make_asset(self.user, acquisition_value=Decimal('100.00'))
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.context['patrimonio'], Decimal('100.00'))
