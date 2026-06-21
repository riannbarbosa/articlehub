"""Testes automatizados do Banco de Ideias.

Cobrem:
- RF03: CRUD de ideias
- RF04: busca global e filtro por tag
- RN02: ideia é independente, sem vínculo obrigatório a um artigo
- isolamento de dados por usuário e exigência de login
"""
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from articles.models import Articles, Tag

from .models import Idea


class AuthRequiredTests(TestCase):
    def test_index_redirects_anonymous_to_login(self):
        resp = self.client.get(reverse('ideas-index'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp['Location'])


class IdeaCrudTests(TestCase):
    """RF03: criação, edição e exclusão de ideias."""

    def setUp(self):
        self.user = User.objects.create_user('rian', password='pw12345678')
        self.client.force_login(self.user)

    def test_create_idea_without_article(self):
        # RN02: a ideia pode existir sem vínculo a um artigo.
        resp = self.client.post(reverse('ideas-index'), {
            'title': 'Conexão entre dois papers', 'content': 'Insight solto.',
            'article': '', 'tags': 'insight',
        })
        self.assertEqual(resp.status_code, 302)
        idea = Idea.objects.get(title='Conexão entre dois papers')
        self.assertEqual(idea.user, self.user)
        self.assertIsNone(idea.article)
        self.assertEqual(set(idea.tags.values_list('name', flat=True)), {'insight'})

    def test_create_idea_linked_to_article(self):
        article = Articles.objects.create(
            user=self.user, title='Base', author='A', year=2020, link='https://e.com')
        resp = self.client.post(reverse('ideas-index'), {
            'title': 'Ideia vinculada', 'content': 'x', 'article': str(article.pk), 'tags': '',
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Idea.objects.get(title='Ideia vinculada').article, article)

    def test_create_idea_invalid_keeps_modal_open(self):
        resp = self.client.post(reverse('ideas-index'),
                                {'title': '', 'content': 'x', 'article': '', 'tags': ''})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['show_modal'])
        self.assertEqual(Idea.objects.count(), 0)

    def test_edit_idea(self):
        idea = Idea.objects.create(user=self.user, title='Antiga', content='c')
        resp = self.client.post(reverse('ideas-edit', args=[idea.pk]), {
            'title': 'Atualizada', 'content': 'c', 'article': '', 'tags': '',
        })
        self.assertEqual(resp.status_code, 302)
        idea.refresh_from_db()
        self.assertEqual(idea.title, 'Atualizada')

    def test_delete_idea(self):
        idea = Idea.objects.create(user=self.user, title='Apagar', content='c')
        resp = self.client.post(reverse('ideas-delete', args=[idea.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Idea.objects.filter(pk=idea.pk).exists())

    def test_bulk_delete(self):
        i1 = Idea.objects.create(user=self.user, title='I1', content='c')
        i2 = Idea.objects.create(user=self.user, title='I2', content='c')
        i3 = Idea.objects.create(user=self.user, title='I3', content='c')
        resp = self.client.post(reverse('ideas-bulk-delete'),
                                {'selected': [str(i1.pk), str(i2.pk)]})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(set(Idea.objects.values_list('pk', flat=True)), {i3.pk})


class IdeaScopingTests(TestCase):
    """A ideia só pode vincular artigos do próprio usuário e respeita isolamento."""

    def setUp(self):
        self.user = User.objects.create_user('rian', password='pw12345678')
        self.other = User.objects.create_user('other', password='pw12345678')
        self.client.force_login(self.user)

    def test_article_choices_limited_to_own_articles(self):
        mine = Articles.objects.create(
            user=self.user, title='Meu', author='A', year=2020, link='https://e.com')
        Articles.objects.create(
            user=self.other, title='Alheio', author='B', year=2020, link='https://e.com')
        resp = self.client.get(reverse('ideas-index'))
        choices = set(resp.context['form'].fields['article'].queryset)
        self.assertEqual(choices, {mine})

    def test_intruder_cannot_edit_others_idea(self):
        idea = Idea.objects.create(user=self.other, title='Privada', content='c')
        resp = self.client.get(reverse('ideas-edit', args=[idea.pk]))
        self.assertEqual(resp.status_code, 404)


class IdeaSearchAndTagTests(TestCase):
    """RF04: busca por palavra-chave e filtro por tag nas ideias."""

    def setUp(self):
        self.user = User.objects.create_user('rian', password='pw12345678')
        self.client.force_login(self.user)
        self.t_ideia = Tag.objects.create(name='insight')
        self.t_duvida = Tag.objects.create(name='duvida')

        self.a = Idea.objects.create(user=self.user, title='Gargalo de memória',
                                     content='Pensar em cache distribuído.')
        self.a.tags.add(self.t_ideia)
        self.b = Idea.objects.create(user=self.user, title='Revisar prova',
                                     content='Conferir o lema central.')
        self.b.tags.add(self.t_ideia, self.t_duvida)

    def _titles(self, resp):
        return {i.title for i in resp.context['ideas']}

    def test_search_by_title(self):
        resp = self.client.get(reverse('ideas-index'), {'q': 'gargalo'})
        self.assertEqual(self._titles(resp), {'Gargalo de memória'})

    def test_search_by_content(self):
        resp = self.client.get(reverse('ideas-index'), {'q': 'lema'})
        self.assertEqual(self._titles(resp), {'Revisar prova'})

    def test_filter_two_tags_is_and(self):
        resp = self.client.get(reverse('ideas-index'), {'tag': ['insight', 'duvida']})
        self.assertEqual(self._titles(resp), {'Revisar prova'})
