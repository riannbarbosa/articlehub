"""Testes automatizados do app de Artigos.

Cobrem os requisitos da proposta:
- RF01: CRUD de artigos
- RF02: editor de fichamento (Annotation)
- RF04: busca global e filtro por tag
- RN01: fichamento sempre vinculado a um artigo
- RNF: isolamento de dados por usuário e exigência de login
"""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Annotation, Articles, Tag


def make_article(user, title='Artigo', author='Autor', year=2024, **kwargs):
    return Articles.objects.create(
        user=user, title=title, author=author, year=year,
        link=kwargs.pop('link', 'https://example.com'), **kwargs,
    )


class AuthRequiredTests(TestCase):
    """Todas as telas de artigos exigem login."""

    def test_index_redirects_anonymous_to_login(self):
        resp = self.client.get(reverse('articles-index'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp['Location'])

    def test_annotation_redirects_anonymous_to_login(self):
        article = make_article(User.objects.create_user('owner', password='pw12345678'))
        resp = self.client.get(reverse('articles-annotation', args=[article.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp['Location'])


class ArticleCrudTests(TestCase):
    """RF01: cadastro, edição e exclusão de artigos."""

    def setUp(self):
        self.user = User.objects.create_user('rian', password='pw12345678')
        self.client.force_login(self.user)

    def test_create_article(self):
        resp = self.client.post(reverse('articles-index'), {
            'title': 'Deep Learning', 'author': 'Goodfellow', 'year': 2016,
            'link': 'https://example.com', 'tags': 'ml, ia',
        })
        self.assertEqual(resp.status_code, 302)
        article = Articles.objects.get(title='Deep Learning')
        self.assertEqual(article.user, self.user)
        # As tags informadas como texto viram objetos Tag associados.
        self.assertEqual(set(article.tags.values_list('name', flat=True)), {'ml', 'ia'})

    def test_create_article_invalid_keeps_modal_open(self):
        resp = self.client.post(reverse('articles-index'), {
            'title': '', 'author': 'X', 'year': 2020, 'link': 'https://e.com',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['show_modal'])
        self.assertEqual(Articles.objects.count(), 0)

    def test_edit_article(self):
        article = make_article(self.user, title='Antigo')
        resp = self.client.post(reverse('articles-edit', args=[article.pk]), {
            'title': 'Novo título', 'author': 'Autor', 'year': 2024,
            'link': 'https://example.com', 'tags': '',
        })
        self.assertEqual(resp.status_code, 302)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Novo título')

    def test_delete_article(self):
        article = make_article(self.user)
        resp = self.client.post(reverse('articles-delete', args=[article.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Articles.objects.filter(pk=article.pk).exists())

    def test_delete_requires_post(self):
        article = make_article(self.user)
        resp = self.client.get(reverse('articles-delete', args=[article.pk]))
        self.assertEqual(resp.status_code, 405)
        self.assertTrue(Articles.objects.filter(pk=article.pk).exists())

    def test_bulk_delete(self):
        a1 = make_article(self.user, title='A1')
        a2 = make_article(self.user, title='A2')
        a3 = make_article(self.user, title='A3')
        resp = self.client.post(reverse('articles-bulk-delete'),
                                {'selected': [str(a1.pk), str(a2.pk)]})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(set(Articles.objects.values_list('pk', flat=True)), {a3.pk})


class UserIsolationTests(TestCase):
    """Um usuário nunca acessa ou altera artigos de outro."""

    def setUp(self):
        self.owner = User.objects.create_user('owner', password='pw12345678')
        self.intruder = User.objects.create_user('intruder', password='pw12345678')
        self.article = make_article(self.owner, title='Privado')
        self.client.force_login(self.intruder)

    def test_intruder_cannot_see_others_article_in_list(self):
        resp = self.client.get(reverse('articles-index'))
        self.assertNotContains(resp, 'Privado')

    def test_intruder_cannot_edit_others_article(self):
        resp = self.client.get(reverse('articles-edit', args=[self.article.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_intruder_cannot_delete_others_article(self):
        resp = self.client.post(reverse('articles-delete', args=[self.article.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Articles.objects.filter(pk=self.article.pk).exists())


class SearchAndTagFilterTests(TestCase):
    """RF04: busca global por palavra-chave e filtro por tag."""

    def setUp(self):
        self.user = User.objects.create_user('rian', password='pw12345678')
        self.client.force_login(self.user)
        self.ml = Tag.objects.create(name='ml')
        self.nlp = Tag.objects.create(name='nlp')

        self.a = make_article(self.user, title='Redes Neurais', author='Hinton')
        self.a.tags.add(self.ml)
        self.b = make_article(self.user, title='Tradução automática', author='Bahdanau')
        self.b.tags.add(self.ml, self.nlp)
        # Fichamento usado para testar busca por conteúdo do fichamento.
        Annotation.objects.create(article=self.a, user=self.user,
                                  content='Contém o termo backpropagation no resumo.')

    def _titles(self, resp):
        return {a.title for a in resp.context['articles']}

    def test_search_by_title(self):
        resp = self.client.get(reverse('articles-index'), {'q': 'tradução'})
        self.assertEqual(self._titles(resp), {'Tradução automática'})

    def test_search_by_author(self):
        resp = self.client.get(reverse('articles-index'), {'q': 'hinton'})
        self.assertEqual(self._titles(resp), {'Redes Neurais'})

    def test_search_by_annotation_content(self):
        resp = self.client.get(reverse('articles-index'), {'q': 'backpropagation'})
        self.assertEqual(self._titles(resp), {'Redes Neurais'})

    def test_filter_single_tag(self):
        resp = self.client.get(reverse('articles-index'), {'tag': 'ml'})
        self.assertEqual(self._titles(resp), {'Redes Neurais', 'Tradução automática'})

    def test_filter_two_tags_is_and(self):
        # Só o artigo que possui AMBAS as tags deve aparecer.
        resp = self.client.get(reverse('articles-index'), {'tag': ['ml', 'nlp']})
        self.assertEqual(self._titles(resp), {'Tradução automática'})

    def test_available_tags_are_scoped_to_user(self):
        other = User.objects.create_user('other', password='pw12345678')
        only_other = Tag.objects.create(name='exclusiva')
        make_article(other).tags.add(only_other)
        resp = self.client.get(reverse('articles-index'))
        names = {chip['name'] for chip in resp.context['tag_chips']}
        self.assertEqual(names, {'ml', 'nlp'})


class AnnotationTests(TestCase):
    """RF02: editor de fichamento. RN01: fichamento vinculado ao artigo."""

    def setUp(self):
        self.user = User.objects.create_user('rian', password='pw12345678')
        self.client.force_login(self.user)
        self.article = make_article(self.user, title='Artigo com fichamento')
        self.url = reverse('articles-annotation', args=[self.article.pk])

    def test_get_shows_new_form_when_no_annotation(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['has_annotation'])

    def test_create_annotation(self):
        resp = self.client.post(self.url, {'content': 'Resumo crítico do artigo.'})
        self.assertEqual(resp.status_code, 302)
        annotation = Annotation.objects.get(article=self.article)
        self.assertEqual(annotation.content, 'Resumo crítico do artigo.')
        self.assertEqual(annotation.user, self.user)

    def test_edit_keeps_single_annotation(self):
        Annotation.objects.create(article=self.article, user=self.user, content='v1')
        resp = self.client.post(self.url, {'content': 'v2'})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Annotation.objects.filter(article=self.article).count(), 1)
        self.assertEqual(Annotation.objects.get(article=self.article).content, 'v2')

    def test_empty_content_is_rejected(self):
        resp = self.client.post(self.url, {'content': '   '})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Annotation.objects.filter(article=self.article).exists())

    def test_delete_annotation(self):
        Annotation.objects.create(article=self.article, user=self.user, content='abc')
        resp = self.client.post(self.url, {'delete': '1'})
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Annotation.objects.filter(article=self.article).exists())

    def test_cannot_edit_annotation_of_other_user(self):
        other = User.objects.create_user('other', password='pw12345678')
        other_article = make_article(other)
        resp = self.client.get(reverse('articles-annotation', args=[other_article.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_badge_shown_in_list_when_annotation_exists(self):
        Annotation.objects.create(article=self.article, user=self.user, content='abc')
        resp = self.client.get(reverse('articles-index'))
        self.assertContains(resp, 'annotation-badge')


class DoiLookupTests(TestCase):
    """Endpoint JSON de busca de metadados por DOI (RF01, autopreenchimento)."""

    def setUp(self):
        self.user = User.objects.create_user('rian', password='pw12345678')
        self.client.force_login(self.user)

    def test_empty_doi_returns_400(self):
        resp = self.client.get(reverse('lookup-doi'), {'doi': ''})
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.json())

    @patch('articles.crossref.lookup')
    def test_valid_doi_returns_metadata(self, mock_lookup):
        mock_lookup.return_value = {
            'doi': '10.1/x', 'title': 'Título', 'author': 'Autor',
            'year': 2020, 'link': 'https://doi.org/10.1/x',
        }
        resp = self.client.get(reverse('lookup-doi'), {'doi': '10.1/x'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['title'], 'Título')

    @patch('articles.crossref.lookup', side_effect=LookupError('não encontrado'))
    def test_unknown_doi_returns_404(self, _mock):
        resp = self.client.get(reverse('lookup-doi'), {'doi': '10.0/missing'})
        self.assertEqual(resp.status_code, 404)
