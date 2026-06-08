from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.text import slugify

from empresa.models import Empresa, MembroEmpresa
from financeiro.models import CentroCusto, Despesa, FormaPagamento, Repasse, SubGrupo
from financeiro.forms import DespesaForm, RepasseForm


# ── helpers ────────────────────────────────────────────────────────────────────

def make_user(username='user', password='senha123'):
    return User.objects.create_user(username=username, password=password)


def make_empresa(nome='Empresa Teste', ativa=True):
    return Empresa.objects.create(nome=nome, slug=slugify(nome), ativa=ativa)


def make_membro(user, empresa, perfil='admin'):
    return MembroEmpresa.objects.create(empresa=empresa, user=user, perfil=perfil)


def make_despesa(user, empresa, **kwargs):
    defaults = dict(
        data=date(2026, 6, 1),
        centro_custo='TI',
        subgrupo='Software',
        descricao='Licença mensal',
        valor=Decimal('500.00'),
        forma_pagamento='Pix',
        situacao=Despesa.Situacao.PENDENTE,
    )
    defaults.update(kwargs)
    return Despesa.objects.create(user=user, empresa=empresa, **defaults)


def make_repasse(user, empresa, **kwargs):
    defaults = dict(
        data=date(2026, 6, 1),
        origem='Matriz',
        destino='Filial',
        valor=Decimal('1000.00'),
        tipo=Repasse.Tipo.APORTE,
    )
    defaults.update(kwargs)
    return Repasse.objects.create(user=user, empresa=empresa, **defaults)


# ── Models ─────────────────────────────────────────────────────────────────────

class DespesaModelTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()

    def test_str_contem_descricao_e_valor(self):
        """__str__ deve conter descrição e valor."""
        d = make_despesa(self.user, self.empresa)
        self.assertIn('Licença mensal', str(d))
        self.assertIn('500', str(d))

    def test_situacao_padrao_e_pendente(self):
        """Status padrão de uma despesa deve ser Pendente."""
        d = make_despesa(self.user, self.empresa)
        self.assertEqual(d.situacao, Despesa.Situacao.PENDENTE)

    def test_ordenacao_por_data_desc(self):
        """Despesas devem ser ordenadas pela data mais recente primeiro."""
        make_despesa(self.user, self.empresa, data=date(2026, 5, 1))
        make_despesa(self.user, self.empresa, data=date(2026, 6, 1))
        despesas = list(Despesa.objects.filter(empresa=self.empresa))
        self.assertEqual(despesas[0].data, date(2026, 6, 1))


class RepasseModelTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()

    def test_str_contem_tipo_origem_destino(self):
        """__str__ deve conter tipo, origem e destino."""
        r = make_repasse(self.user, self.empresa)
        self.assertIn('Matriz', str(r))
        self.assertIn('Filial', str(r))

    def test_tipos_disponiveis(self):
        """Deve ter exatamente os tipos Aporte e Repasse."""
        tipos = [t.value for t in Repasse.Tipo]
        self.assertIn('aporte', tipos)
        self.assertIn('repasse', tipos)


class CentroCustoModelTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()

    def test_str_retorna_nome(self):
        """__str__ de CentroCusto deve retornar o nome."""
        c = CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='Financeiro')
        self.assertEqual(str(c), 'Financeiro')

    def test_unique_together_empresa_nome(self):
        """Não deve permitir dois centros com mesmo nome na mesma empresa."""
        from django.db import IntegrityError
        CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='TI')
        with self.assertRaises(IntegrityError):
            CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='TI')


# ── Forms ──────────────────────────────────────────────────────────────────────

class DespesaFormTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()
        CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='TI')
        SubGrupo.objects.create(empresa=self.empresa, user=self.user, nome='Software')
        FormaPagamento.objects.create(empresa=self.empresa, user=self.user, nome='Pix')

    def test_form_valido_com_dados_corretos(self):
        """Formulário deve ser válido com todos os campos corretos."""
        form = DespesaForm(data={
            'data': '2026-06-01', 'centro_custo': 'TI', 'subgrupo': 'Software',
            'descricao': 'Teste', 'valor': '100.00', 'forma_pagamento': 'Pix',
            'situacao': 'pendente',
        }, empresa=self.empresa)
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_invalido_sem_descricao(self):
        """Formulário deve ser inválido sem descrição."""
        form = DespesaForm(data={
            'data': '2026-06-01', 'centro_custo': 'TI', 'subgrupo': 'Software',
            'descricao': '', 'valor': '100.00', 'forma_pagamento': 'Pix',
            'situacao': 'pendente',
        }, empresa=self.empresa)
        self.assertFalse(form.is_valid())
        self.assertIn('descricao', form.errors)

    def test_choices_vindo_da_empresa_correta(self):
        """Choices do form devem vir apenas da empresa passada."""
        outra = make_empresa('Outra')
        CentroCusto.objects.create(empresa=outra, user=self.user, nome='CentroOutra')
        form = DespesaForm(empresa=self.empresa)
        centros = [c for c, _ in form.fields['centro_custo'].choices if c]
        self.assertIn('TI', centros)
        self.assertNotIn('CentroOutra', centros)


class RepasseFormTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()
        CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='Matriz')
        CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='Filial')

    def test_form_valido_com_dados_corretos(self):
        """Formulário de repasse deve ser válido com origem ≠ destino."""
        form = RepasseForm(data={
            'data': '2026-06-01', 'tipo': 'aporte',
            'origem': 'Matriz', 'destino': 'Filial',
            'valor': '1000.00', 'descricao': '',
        }, empresa=self.empresa)
        self.assertTrue(form.is_valid(), form.errors)

    def test_origem_igual_destino_invalido(self):
        """Repasse com origem igual ao destino deve ser inválido."""
        form = RepasseForm(data={
            'data': '2026-06-01', 'tipo': 'aporte',
            'origem': 'Matriz', 'destino': 'Matriz',
            'valor': '1000.00', 'descricao': '',
        }, empresa=self.empresa)
        self.assertFalse(form.is_valid())


# ── Views: autenticação ────────────────────────────────────────────────────────

class FinanceiroAuthTests(TestCase):

    PROTECTED = ['despesa_list', 'despesa_create', 'repasse_list', 'repasse_create', 'financeiro_dashboard']

    def test_views_redirecionam_sem_login(self):
        """Todas as views financeiras devem redirecionar para login sem autenticação."""
        for name in self.PROTECTED:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302, msg=f'{name} deveria redirecionar')
            self.assertIn('/login', resp['Location'])


# ── Views: despesa_list ────────────────────────────────────────────────────────

class DespesaListViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()
        make_membro(self.user, self.empresa)
        self.client.force_login(self.user)
        self.url = reverse('despesa_list')

    def test_retorna_200(self):
        """Lista de despesas deve retornar 200."""
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_exibe_apenas_despesas_da_empresa(self):
        """Deve exibir apenas despesas da empresa do usuário logado."""
        outra_empresa = make_empresa('Outra')
        outro_user = make_user('outro')
        make_despesa(self.user, self.empresa, descricao='Minha Despesa')
        make_despesa(outro_user, outra_empresa, descricao='Despesa Alheia')
        resp = self.client.get(self.url + '?de=2026-01-01&ate=2026-12-31')
        self.assertContains(resp, 'Minha Despesa')
        self.assertNotContains(resp, 'Despesa Alheia')

    def test_filtro_por_periodo(self):
        """Filtro de período deve retornar apenas despesas no intervalo."""
        make_despesa(self.user, self.empresa, data=date(2026, 3, 1), descricao='Marco')
        make_despesa(self.user, self.empresa, data=date(2026, 6, 1), descricao='Junho')
        resp = self.client.get(self.url + '?de=2026-06-01&ate=2026-06-30')
        self.assertContains(resp, 'Junho')
        self.assertNotContains(resp, 'Marco')

    def test_filtro_por_situacao(self):
        """Filtro por situação deve retornar apenas despesas com o status correto."""
        make_despesa(self.user, self.empresa, descricao='DespesaPaga001', situacao='pago')
        make_despesa(self.user, self.empresa, descricao='DespesaPendente001', situacao='pendente')
        resp = self.client.get(self.url + '?de=2026-01-01&ate=2026-12-31&situacao=pago')
        self.assertContains(resp, 'DespesaPaga001')
        self.assertNotContains(resp, 'DespesaPendente001')


# ── Views: despesa create/edit/delete ─────────────────────────────────────────

class DespesaCRUDTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()
        make_membro(self.user, self.empresa)
        CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='TI')
        SubGrupo.objects.create(empresa=self.empresa, user=self.user, nome='Software')
        FormaPagamento.objects.create(empresa=self.empresa, user=self.user, nome='Pix')
        self.client.force_login(self.user)

    def test_criar_despesa_via_post(self):
        """POST válido deve criar despesa e redirecionar."""
        resp = self.client.post(reverse('despesa_create'), {
            'data': '2026-06-01', 'centro_custo': 'TI', 'subgrupo': 'Software',
            'descricao': 'Nova despesa', 'valor': '250.00',
            'forma_pagamento': 'Pix', 'situacao': 'pendente',
        })
        self.assertRedirects(resp, reverse('despesa_list'))
        self.assertTrue(Despesa.objects.filter(descricao='Nova despesa').exists())

    def test_deletar_despesa(self):
        """POST no delete deve remover a despesa."""
        d = make_despesa(self.user, self.empresa)
        self.client.post(reverse('despesa_delete', args=[d.pk]))
        self.assertFalse(Despesa.objects.filter(pk=d.pk).exists())

    def test_nao_deleta_despesa_de_outra_empresa(self):
        """Não deve permitir deletar despesa de empresa diferente."""
        outro_user = make_user('outro')
        outra = make_empresa('Outra')
        d = make_despesa(outro_user, outra)
        resp = self.client.post(reverse('despesa_delete', args=[d.pk]))
        self.assertEqual(resp.status_code, 404)


# ── Views: repasse ─────────────────────────────────────────────────────────────

class RepasseCRUDTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()
        make_membro(self.user, self.empresa)
        CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='Matriz')
        CentroCusto.objects.create(empresa=self.empresa, user=self.user, nome='Filial')
        self.client.force_login(self.user)

    def test_criar_repasse_via_post(self):
        """POST válido deve criar repasse e redirecionar."""
        resp = self.client.post(reverse('repasse_create'), {
            'data': '2026-06-01', 'tipo': 'aporte',
            'origem': 'Matriz', 'destino': 'Filial',
            'valor': '2000.00', 'descricao': '',
        })
        self.assertRedirects(resp, reverse('repasse_list'))
        self.assertTrue(Repasse.objects.filter(origem='Matriz', destino='Filial').exists())

    def test_origem_igual_destino_nao_cria(self):
        """Repasse com origem = destino não deve ser criado."""
        self.client.post(reverse('repasse_create'), {
            'data': '2026-06-01', 'tipo': 'aporte',
            'origem': 'Matriz', 'destino': 'Matriz',
            'valor': '500.00', 'descricao': '',
        })
        self.assertFalse(Repasse.objects.filter(origem='Matriz', destino='Matriz').exists())

    def test_deletar_repasse(self):
        """POST no delete deve remover o repasse."""
        r = make_repasse(self.user, self.empresa)
        self.client.post(reverse('repasse_delete', args=[r.pk]))
        self.assertFalse(Repasse.objects.filter(pk=r.pk).exists())
