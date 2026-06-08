from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from empresa.models import Empresa, MembroEmpresa


def make_user(username='testuser', password='senha123', **kwargs):
    return User.objects.create_user(username=username, password=password, **kwargs)


def make_empresa(nome='Empresa Teste', ativa=True):
    from django.utils.text import slugify
    return Empresa.objects.create(nome=nome, slug=slugify(nome), ativa=ativa)


class LoginViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.url = reverse('login')

    # ── GET ────────────────────────────────────────────────────────────────────

    def test_get_retorna_200(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)

    def test_get_usa_template_correto(self):
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, 'accounts/login.html')

    # ── Happy path ─────────────────────────────────────────────────────────────

    def test_login_valido_redireciona(self):
        make_user()
        resp = self.client.post(self.url, {'username': 'testuser', 'password': 'senha123'})
        self.assertEqual(resp.status_code, 302)

    def test_login_valido_usuario_autenticado(self):
        make_user()
        self.client.post(self.url, {'username': 'testuser', 'password': 'senha123'})
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)

    # ── Credenciais inválidas ──────────────────────────────────────────────────

    def test_senha_errada_redireciona_para_login(self):
        make_user()
        resp = self.client.post(self.url, {'username': 'testuser', 'password': 'errada'})
        self.assertRedirects(resp, self.url)

    def test_senha_errada_exibe_mensagem_de_erro(self):
        make_user()
        self.client.post(self.url, {'username': 'testuser', 'password': 'errada'})
        resp = self.client.get(self.url)
        self.assertContains(resp, 'inválidos')

    def test_usuario_inexistente_nao_autentica(self):
        resp = self.client.post(self.url, {'username': 'naoexiste', 'password': 'qualquer'})
        self.assertRedirects(resp, self.url)

    # ── Brute-force lockout ────────────────────────────────────────────────────

    def test_lockout_apos_max_tentativas(self):
        make_user()
        for _ in range(5):
            self.client.post(self.url, {'username': 'testuser', 'password': 'errada'})
        resp = self.client.get(self.url)
        self.assertContains(resp, 'bloqueada')

    def test_lockout_impede_login_correto(self):
        make_user()
        for _ in range(5):
            self.client.post(self.url, {'username': 'testuser', 'password': 'errada'})
        resp = self.client.post(self.url, {'username': 'testuser', 'password': 'senha123'})
        self.assertRedirects(resp, self.url)

    # ── Membro inativo ─────────────────────────────────────────────────────────

    def test_membro_inativo_nao_entra(self):
        user = make_user(username='inativo')
        empresa = make_empresa()
        MembroEmpresa.objects.create(empresa=empresa, user=user, perfil='operador', ativo=False)
        resp = self.client.post(self.url, {'username': 'inativo', 'password': 'senha123'}, follow=True)
        self.assertContains(resp, 'inativo')

    def test_empresa_inativa_bloqueia_login(self):
        user = make_user(username='bloqueado')
        empresa = make_empresa(ativa=False)
        MembroEmpresa.objects.create(empresa=empresa, user=user, perfil='operador', ativo=True)
        resp = self.client.post(self.url, {'username': 'bloqueado', 'password': 'senha123'}, follow=True)
        self.assertContains(resp, 'inativo')

    def test_superuser_entra_mesmo_sem_empresa(self):
        User.objects.create_superuser(username='admin', password='admin123')
        resp = self.client.post(self.url, {'username': 'admin', 'password': 'admin123'})
        self.assertEqual(resp.status_code, 302)
        self.assertNotEqual(resp['Location'], self.url)

    def test_superuser_entra_com_empresa_inativa(self):
        admin = User.objects.create_superuser(username='admin2', password='admin123')
        empresa = make_empresa(ativa=False)
        MembroEmpresa.objects.create(empresa=empresa, user=admin, perfil='admin', ativo=False)
        resp = self.client.post(self.url, {'username': 'admin2', 'password': 'admin123'})
        self.assertEqual(resp.status_code, 302)
        self.assertNotEqual(resp['Location'], self.url)


class LogoutViewTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client.force_login(self.user)

    def test_post_desloga_e_redireciona(self):
        resp = self.client.post(reverse('logout'))
        self.assertRedirects(resp, reverse('login'))

    def test_get_nao_desloga(self):
        """GET no logout não deve deslogar (proteção CSRF)."""
        self.client.get(reverse('logout'))
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)


class HomeViewTests(TestCase):

    def test_home_requer_autenticacao(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp['Location'])

    def test_home_autenticado_retorna_200(self):
        self.client.force_login(make_user())
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)


class PasswordChangeViewTests(TestCase):

    def setUp(self):
        self.user = make_user(password='senhaAntiga1')
        self.client.force_login(self.user)
        self.url = reverse('password_change')

    def test_get_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_get_usa_template_correto(self):
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, 'registration/password_change_form.html')

    def test_anonimo_redireciona_para_login(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp['Location'])

    def test_senha_alterada_com_sucesso(self):
        resp = self.client.post(self.url, {
            'old_password': 'senhaAntiga1',
            'new_password1': 'NovaSenha@456',
            'new_password2': 'NovaSenha@456',
        })
        self.assertRedirects(resp, reverse('password_change_done'))

    def test_nova_senha_funciona_no_login(self):
        self.client.post(self.url, {
            'old_password': 'senhaAntiga1',
            'new_password1': 'NovaSenha@456',
            'new_password2': 'NovaSenha@456',
        })
        self.client.logout()
        resp = self.client.post(reverse('login'), {
            'username': 'testuser', 'password': 'NovaSenha@456',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertNotEqual(resp['Location'], reverse('login'))

    def test_senha_antiga_errada_nao_altera(self):
        self.client.post(self.url, {
            'old_password': 'errada',
            'new_password1': 'NovaSenha@456',
            'new_password2': 'NovaSenha@456',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('senhaAntiga1'))

    def test_senhas_divergentes_nao_alteram(self):
        self.client.post(self.url, {
            'old_password': 'senhaAntiga1',
            'new_password1': 'NovaSenha@456',
            'new_password2': 'Diferente@789',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('senhaAntiga1'))


class PasswordChangeDoneViewTests(TestCase):

    def setUp(self):
        self.client.force_login(make_user())
        self.url = reverse('password_change_done')

    def test_get_retorna_200(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_usa_template_correto(self):
        resp = self.client.get(self.url)
        self.assertTemplateUsed(resp, 'registration/password_change_done.html')

    def test_anonimo_redireciona(self):
        self.client.logout()
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)
