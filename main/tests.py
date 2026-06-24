"""Testes de autenticação: login (por e-mail), cadastro com OTP e logout."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

# Senha válida pelas regras do cadastro: >= 8 caracteres e um especial.
VALID_PASSWORD = 'pw123456!'


class LoginTests(TestCase):
    def setUp(self):
        # O login é por e-mail, então a conta precisa ter um e-mail.
        self.user = User.objects.create_user(
            'rian', email='rian@e.com', password=VALID_PASSWORD)

    def test_login_success_redirects_to_articles(self):
        resp = self.client.post(reverse('login'),
                                {'email': 'rian@e.com', 'password': VALID_PASSWORD})
        self.assertRedirects(resp, reverse('articles-index'))

    def test_login_invalid_credentials_stays(self):
        resp = self.client.post(reverse('login'),
                                {'email': 'rian@e.com', 'password': 'errada'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.wsgi_request.user.is_authenticated)

    def test_authenticated_user_redirected_away_from_login(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('login'))
        self.assertRedirects(resp, reverse('articles-index'))


class RegisterTests(TestCase):
    def _register(self, **overrides):
        data = {
            'name': 'Novo', 'email': 'n@e.com',
            'password1': VALID_PASSWORD, 'password2': VALID_PASSWORD,
        }
        data.update(overrides)
        return self.client.post(reverse('register'), data)

    def test_register_creates_pending_and_redirects_to_verify(self):
        # O cadastro não cria a conta na hora: guarda um cadastro pendente na
        # sessão e manda o usuário para a verificação do código (OTP).
        resp = self._register()
        self.assertRedirects(resp, reverse('verify'))
        self.assertFalse(User.objects.filter(email='n@e.com').exists())
        self.assertIn('pending_registration', self.client.session)

    def test_verify_creates_user_and_logs_in(self):
        self._register()
        code = self.client.session['pending_registration']['code']
        resp = self.client.post(reverse('verify'), {'code': code})
        self.assertRedirects(resp, reverse('articles-index'))
        # username = e-mail (login por e-mail).
        self.assertTrue(User.objects.filter(email='n@e.com').exists())

    def test_register_password_mismatch(self):
        resp = self._register(password2='diferente!')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(email='n@e.com').exists())

    def test_register_short_password(self):
        resp = self._register(password1='cur!', password2='cur!')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(email='n@e.com').exists())

    def test_register_missing_special_char(self):
        resp = self._register(password1='pw12345678', password2='pw12345678')
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(email='n@e.com').exists())

    def test_register_duplicate_email(self):
        User.objects.create_user('existente', email='n@e.com', password=VALID_PASSWORD)
        resp = self._register()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(email='n@e.com').count(), 1)


class LogoutTests(TestCase):
    def test_logout_redirects_to_login(self):
        user = User.objects.create_user('rian', password=VALID_PASSWORD)
        self.client.force_login(user)
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, reverse('login'))
