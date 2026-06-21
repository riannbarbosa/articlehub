"""Testes de autenticação: login, cadastro e logout."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('rian', password='pw12345678')

    def test_login_success_redirects_to_articles(self):
        resp = self.client.post(reverse('login'),
                                {'username': 'rian', 'password': 'pw12345678'})
        self.assertRedirects(resp, reverse('articles-index'))

    def test_login_invalid_credentials_stays(self):
        resp = self.client.post(reverse('login'),
                                {'username': 'rian', 'password': 'errada'})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.wsgi_request.user.is_authenticated)

    def test_authenticated_user_redirected_away_from_login(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse('login'))
        self.assertRedirects(resp, reverse('articles-index'))


class RegisterTests(TestCase):
    def test_register_creates_user_and_logs_in(self):
        resp = self.client.post(reverse('register'), {
            'username': 'novo', 'email': 'n@e.com',
            'password1': 'pw12345678', 'password2': 'pw12345678',
        })
        self.assertRedirects(resp, reverse('articles-index'))
        self.assertTrue(User.objects.filter(username='novo').exists())

    def test_register_password_mismatch(self):
        resp = self.client.post(reverse('register'), {
            'username': 'novo', 'email': 'n@e.com',
            'password1': 'pw12345678', 'password2': 'diferente',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='novo').exists())

    def test_register_short_password(self):
        resp = self.client.post(reverse('register'), {
            'username': 'novo', 'email': 'n@e.com',
            'password1': 'curta', 'password2': 'curta',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username='novo').exists())

    def test_register_duplicate_username(self):
        User.objects.create_user('existente', password='pw12345678')
        resp = self.client.post(reverse('register'), {
            'username': 'existente', 'email': 'n@e.com',
            'password1': 'pw12345678', 'password2': 'pw12345678',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(username='existente').count(), 1)


class LogoutTests(TestCase):
    def test_logout_redirects_to_login(self):
        user = User.objects.create_user('rian', password='pw12345678')
        self.client.force_login(user)
        resp = self.client.get(reverse('logout'))
        self.assertRedirects(resp, reverse('login'))
