from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.text import slugify

from .models import Empresa, MembroEmpresa


# ── helpers ────────────────────────────────────────────────────────────────────

def make_superuser(username='super', password='senha123'):
    return User.objects.create_superuser(username=username, password=password)


def make_user(username='user', password='senha123'):
    return User.objects.create_user(username=username, password=password)


def make_empresa(nome='Empresa Teste', ativa=True):
    return Empresa.objects.create(nome=nome, slug=slugify(nome), ativa=ativa)


def make_membro(user, empresa, perfil='admin', ativo=True):
    return MembroEmpresa.objects.create(empresa=empresa, user=user, perfil=perfil, ativo=ativo)


# ── Autenticação / autorização ─────────────────────────────────────────────────

class SuperAdminAuthTests(TestCase):

    PROTECTED = [
        'superadmin_empresas',
        'superadmin_empresa_criar',
    ]

    def test_anonimo_redireciona_para_login(self):
        for name in self.PROTECTED:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302)
            self.assertIn('/login', resp['Location'])

    def test_usuario_comum_bloqueado(self):
        self.client.force_login(make_user())
        for name in self.PROTECTED:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302)

    def test_superuser_acessa_lista(self):
        self.client.force_login(make_superuser())
        resp = self.client.get(reverse('superadmin_empresas'))
        self.assertEqual(resp.status_code, 200)


# ── superadmin_empresas ────────────────────────────────────────────────────────

class SuperAdminEmpresasListTests(TestCase):

    def setUp(self):
        self.client.force_login(make_superuser())

    def test_lista_todas_empresas(self):
        make_empresa('Alpha')
        make_empresa('Beta')
        resp = self.client.get(reverse('superadmin_empresas'))
        self.assertContains(resp, 'Alpha')
        self.assertContains(resp, 'Beta')

    def test_lista_vazia_nao_quebra(self):
        resp = self.client.get(reverse('superadmin_empresas'))
        self.assertEqual(resp.status_code, 200)


# ── superadmin_empresa_criar ───────────────────────────────────────────────────

class SuperAdminEmpresaCriarTests(TestCase):

    def setUp(self):
        self.client.force_login(make_superuser())
        self.url = reverse('superadmin_empresa_criar')

    def test_get_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_valido_cria_empresa_e_admin(self):
        self.client.post(self.url, {
            'nome': 'Nova Empresa', 'username': 'adminNovo', 'password': 'senha123',
        })
        self.assertTrue(Empresa.objects.filter(nome='Nova Empresa').exists())
        self.assertTrue(User.objects.filter(username='adminNovo').exists())
        membro = MembroEmpresa.objects.get(user__username='adminNovo')
        self.assertEqual(membro.perfil, 'admin')

    def test_post_valido_redireciona_para_lista(self):
        resp = self.client.post(self.url, {
            'nome': 'Empresa X', 'username': 'userx', 'password': 'senha123',
        })
        self.assertRedirects(resp, reverse('superadmin_empresas'))

    def test_post_sem_nome_nao_cria(self):
        self.client.post(self.url, {'nome': '', 'username': 'userx', 'password': 'senha123'})
        self.assertFalse(Empresa.objects.filter(slug='').exists())
        self.assertFalse(User.objects.filter(username='userx').exists())

    def test_post_sem_senha_nao_cria(self):
        self.client.post(self.url, {'nome': 'Empresa Y', 'username': 'usery', 'password': ''})
        self.assertFalse(Empresa.objects.filter(nome='Empresa Y').exists())

    def test_username_duplicado_nao_cria_empresa(self):
        make_user('existente')
        self.client.post(self.url, {
            'nome': 'Empresa Dup', 'username': 'existente', 'password': 'senha123',
        })
        self.assertFalse(Empresa.objects.filter(nome='Empresa Dup').exists())

    def test_slug_gerado_automaticamente(self):
        self.client.post(self.url, {
            'nome': 'Minha Empresa Legal', 'username': 'userslug', 'password': 'senha123',
        })
        self.assertTrue(Empresa.objects.filter(slug='minha-empresa-legal').exists())

    def test_slugs_unicos_em_nomes_iguais(self):
        make_empresa('Duplicada')  # slug='duplicada' já existe
        self.client.post(self.url, {
            'nome': 'Duplicada', 'username': 'userdup2', 'password': 'senha123',
        })
        self.assertTrue(Empresa.objects.filter(slug='duplicada-1').exists())


# ── superadmin_empresa_detalhe ─────────────────────────────────────────────────

class SuperAdminEmpresaDetalheTests(TestCase):

    def setUp(self):
        self.client.force_login(make_superuser())
        self.empresa = make_empresa()
        self.url = reverse('superadmin_empresa_detalhe', args=[self.empresa.pk])

    def test_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_exibe_membros(self):
        user = make_user('membro1')
        make_membro(user, self.empresa)
        resp = self.client.get(self.url)
        self.assertContains(resp, 'membro1')

    def test_empresa_inexistente_retorna_404(self):
        resp = self.client.get(reverse('superadmin_empresa_detalhe', args=[9999]))
        self.assertEqual(resp.status_code, 404)


# ── superadmin_empresa_editar ──────────────────────────────────────────────────

class SuperAdminEmpresaEditarTests(TestCase):

    def setUp(self):
        self.client.force_login(make_superuser())
        self.empresa = make_empresa('Original')
        self.url = reverse('superadmin_empresa_editar', args=[self.empresa.pk])

    def test_get_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_atualiza_nome(self):
        self.client.post(self.url, {'nome': 'Atualizada'})
        self.empresa.refresh_from_db()
        self.assertEqual(self.empresa.nome, 'Atualizada')

    def test_post_redireciona_para_detalhe(self):
        resp = self.client.post(self.url, {'nome': 'Novo Nome'})
        self.assertRedirects(resp, reverse('superadmin_empresa_detalhe', args=[self.empresa.pk]))

    def test_post_remover_logo(self):
        self.empresa.logo = 'logos/fake.png'
        self.empresa.save()
        self.client.post(self.url, {'nome': 'Original', 'remover_logo': '1'})
        self.empresa.refresh_from_db()
        self.assertFalse(self.empresa.logo)


# ── superadmin_empresa_toggle ──────────────────────────────────────────────────

class SuperAdminEmpresaToggleTests(TestCase):

    def setUp(self):
        self.client.force_login(make_superuser())

    def test_toggle_desativa_empresa_ativa(self):
        empresa = make_empresa(ativa=True)
        self.client.post(reverse('superadmin_empresa_toggle', args=[empresa.pk]))
        empresa.refresh_from_db()
        self.assertFalse(empresa.ativa)

    def test_toggle_ativa_empresa_inativa(self):
        empresa = make_empresa(ativa=False)
        self.client.post(reverse('superadmin_empresa_toggle', args=[empresa.pk]))
        empresa.refresh_from_db()
        self.assertTrue(empresa.ativa)

    def test_get_nao_altera_estado(self):
        empresa = make_empresa(ativa=True)
        self.client.get(reverse('superadmin_empresa_toggle', args=[empresa.pk]))
        empresa.refresh_from_db()
        self.assertTrue(empresa.ativa)

    def test_toggle_redireciona_para_lista(self):
        empresa = make_empresa()
        resp = self.client.post(reverse('superadmin_empresa_toggle', args=[empresa.pk]))
        self.assertRedirects(resp, reverse('superadmin_empresas'))


# ── superadmin_membro_editar ───────────────────────────────────────────────────

class SuperAdminMembroEditarTests(TestCase):

    def setUp(self):
        self.client.force_login(make_superuser())
        self.empresa = make_empresa()
        self.user = make_user('membro')
        self.membro = make_membro(self.user, self.empresa, perfil='operador')
        self.url = reverse('superadmin_membro_editar', args=[self.membro.pk])

    def test_get_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_atualiza_perfil(self):
        self.client.post(self.url, {'perfil': 'admin', 'ativo': '1'})
        self.membro.refresh_from_db()
        self.assertEqual(self.membro.perfil, 'admin')

    def test_post_desativa_membro(self):
        self.client.post(self.url, {'perfil': 'operador', 'ativo': '0'})
        self.membro.refresh_from_db()
        self.assertFalse(self.membro.ativo)

    def test_post_redireciona_para_detalhe_empresa(self):
        resp = self.client.post(self.url, {'perfil': 'admin', 'ativo': '1'})
        self.assertRedirects(resp, reverse('superadmin_empresa_detalhe', args=[self.empresa.pk]))


# ── /empresa/usuarios/ ─────────────────────────────────────────────────────────

class UsuariosAuthTests(TestCase):

    PROTECTED = ['usuarios_list', 'usuario_convidar']

    def test_anonimo_redireciona(self):
        for name in self.PROTECTED:
            resp = self.client.get(reverse(name))
            self.assertEqual(resp.status_code, 302)
            self.assertIn('/login', resp['Location'])

    def test_sem_empresa_redireciona_para_setup(self):
        self.client.force_login(make_user('semempresa'))
        for name in self.PROTECTED:
            resp = self.client.get(reverse(name))
            self.assertRedirects(resp, reverse('setup_empresa'))

    def test_operador_bloqueado(self):
        user = make_user('operador')
        empresa = make_empresa()
        make_membro(user, empresa, perfil='operador')
        self.client.force_login(user)
        resp = self.client.get(reverse('usuarios_list'))
        self.assertEqual(resp.status_code, 302)


class UsuariosListTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()
        make_membro(self.user, self.empresa, perfil='admin')
        self.client.force_login(self.user)

    def test_retorna_200(self):
        self.assertEqual(self.client.get(reverse('usuarios_list')).status_code, 200)

    def test_exibe_membros_da_empresa(self):
        outro = make_user('outro')
        make_membro(outro, self.empresa, perfil='operador')
        resp = self.client.get(reverse('usuarios_list'))
        self.assertContains(resp, 'outro')

    def test_nao_exibe_membros_de_outra_empresa(self):
        outra = make_empresa('Outra')
        externo = make_user('externo')
        make_membro(externo, outra, perfil='operador')
        resp = self.client.get(reverse('usuarios_list'))
        self.assertNotContains(resp, 'externo')


class UsuarioConvidarTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.empresa = make_empresa()
        make_membro(self.user, self.empresa, perfil='admin')
        self.client.force_login(self.user)
        self.url = reverse('usuario_convidar')

    def test_get_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_cria_usuario_e_membro(self):
        self.client.post(self.url, {
            'username': 'novomembro', 'password': 'senha123', 'perfil': 'operador',
        })
        self.assertTrue(User.objects.filter(username='novomembro').exists())
        self.assertTrue(MembroEmpresa.objects.filter(
            user__username='novomembro', empresa=self.empresa
        ).exists())

    def test_post_redireciona_para_lista(self):
        resp = self.client.post(self.url, {
            'username': 'novomembro2', 'password': 'senha123', 'perfil': 'operador',
        })
        self.assertRedirects(resp, reverse('usuarios_list'))

    def test_username_duplicado_nao_cria(self):
        make_user('jaexiste')
        self.client.post(self.url, {
            'username': 'jaexiste', 'password': 'senha123', 'perfil': 'operador',
        })
        self.assertEqual(User.objects.filter(username='jaexiste').count(), 1)

    def test_sem_username_nao_cria(self):
        self.client.post(self.url, {'username': '', 'password': 'senha123', 'perfil': 'operador'})
        self.assertFalse(MembroEmpresa.objects.filter(empresa=self.empresa).exclude(user=self.user).exists())

    def test_sem_senha_nao_cria(self):
        self.client.post(self.url, {'username': 'nouser', 'password': '', 'perfil': 'operador'})
        self.assertFalse(User.objects.filter(username='nouser').exists())


class UsuarioEditarTests(TestCase):

    def setUp(self):
        self.admin = make_user('admin')
        self.empresa = make_empresa()
        make_membro(self.admin, self.empresa, perfil='admin')
        self.client.force_login(self.admin)
        self.membro_user = make_user('membro')
        self.membro = make_membro(self.membro_user, self.empresa, perfil='operador')
        self.url = reverse('usuario_editar', args=[self.membro.pk])

    def test_get_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_atualiza_perfil(self):
        self.client.post(self.url, {'perfil': 'admin', 'ativo': '1'})
        self.membro.refresh_from_db()
        self.assertEqual(self.membro.perfil, 'admin')

    def test_post_desativa_membro(self):
        self.client.post(self.url, {'perfil': 'operador', 'ativo': '0'})
        self.membro.refresh_from_db()
        self.assertFalse(self.membro.ativo)

    def test_post_redireciona_para_lista(self):
        resp = self.client.post(self.url, {'perfil': 'operador', 'ativo': '1'})
        self.assertRedirects(resp, reverse('usuarios_list'))

    def test_nao_edita_membro_de_outra_empresa(self):
        outra = make_empresa('Outra')
        externo = make_user('externo')
        membro_externo = make_membro(externo, outra, perfil='operador')
        resp = self.client.get(reverse('usuario_editar', args=[membro_externo.pk]))
        self.assertEqual(resp.status_code, 404)
