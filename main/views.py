from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from urllib.parse import urlencode

from articles.models import Annotation, Articles
from ideas.models import Idea


def _filtered(url_name, **params):
    """URL de uma listagem com a querystring de filtro (?q= ou ?tag=)."""
    return reverse(url_name) + '?' + urlencode(params)


def index(request):
    return render(request, 'index.html')


@login_required
def graph_view(request):
    """Grafo estilo Obsidian: liga artigos aos seus fichamentos, insights e
    tags. As tags funcionam como hubs que conectam itens de temas em comum."""
    user = request.user
    articles = Articles.objects.filter(user=user).prefetch_related('tags')
    ideas = Idea.objects.filter(user=user).prefetch_related('tags')
    annotations = Annotation.objects.filter(user=user).select_related('article')

    nodes = []
    links = []
    used_tags = {}

    for article in articles:
        nodes.append({
            'id': f'a:{article.pk}',
            'label': article.title,
            'type': 'article',
            # Abre a lista de artigos já filtrada por este artigo.
            'url': _filtered('articles-index', q=article.title),
        })
        for tag in article.tags.all():
            used_tags[str(tag.pk)] = tag.name
            links.append({'source': f'a:{article.pk}', 'target': f't:{tag.pk}'})

    for annotation in annotations:
        node_id = f'n:{annotation.pk}'
        nodes.append({
            'id': node_id,
            'label': f'Fichamento — {annotation.article.title}',
            'type': 'annotation',
            # Leva ao artigo do fichamento na lista filtrada.
            'url': _filtered('articles-index', q=annotation.article.title),
        })
        links.append({'source': f'a:{annotation.article.pk}', 'target': node_id})

    for idea in ideas:
        node_id = f'i:{idea.pk}'
        nodes.append({
            'id': node_id,
            'label': idea.title,
            'type': 'idea',
            # Abre o Banco de Ideias já filtrado por este insight.
            'url': _filtered('ideas-index', q=idea.title),
        })
        if idea.article_id:
            links.append({'source': f'a:{idea.article_id}', 'target': node_id})
        for tag in idea.tags.all():
            used_tags[str(tag.pk)] = tag.name
            links.append({'source': node_id, 'target': f't:{tag.pk}'})

    for tag_id, name in used_tags.items():
        nodes.append({
            'id': f't:{tag_id}',
            'label': f'#{name}',
            'type': 'tag',
            # Filtra os artigos por esta tag.
            'url': _filtered('articles-index', tag=name),
        })

    graph = {'nodes': nodes, 'links': links}
    return render(request, 'graph.html', {'graph': graph})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('articles-index')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('articles-index')
        messages.error(request, 'Invalid username or password.')
    return render(request, 'login.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('articles-index')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username:
            messages.error(request, 'Username is required.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        elif password1 != password2:
            messages.error(request, 'Passwords do not match.')
        elif len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters.')
        else:
            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)
            return redirect('articles-index')
    return render(request, 'register.html')


def logout_view(request):
    logout(request)
    return redirect('login')
