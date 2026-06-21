from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.views.decorators.http import require_POST

from . import crossref, tagfilters
from .forms import ArticleForm
from .models import Articles, Tag

ARTICLES_PER_PAGE = 10


@login_required
def index(request):
    """Tela principal: lista os artigos do usuário com busca global (RF04)
    e cadastro de novo artigo via modal (RF01)."""
    form = ArticleForm()
    show_modal = False

    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.user = request.user
            article.save()
            form.save_tags(article)
            messages.success(request, 'Artigo cadastrado com sucesso!')
            return redirect('articles-index')
        # Form inválido: reexibe a tela com o modal aberto e os erros.
        show_modal = True
        messages.error(request, 'Corrija os campos destacados e tente novamente.')

    query = request.GET.get('q', '').strip()
    selected_tags = tagfilters.get_selected_tags(request)
    articles = Articles.objects.filter(user=request.user)

    if query:
        articles = articles.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(annotation__content__icontains=query)
            | Q(tags__name__icontains=query)
        )
    articles = tagfilters.filter_by_tags(articles, selected_tags).distinct()

    # Tags disponíveis para o filtro (apenas as usadas pelos artigos do usuário).
    available_tags = Tag.objects.filter(articles__user=request.user).distinct().order_by('name')
    tag_chips, base_qs = tagfilters.build_tag_chips(available_tags, selected_tags, query)

    total = articles.count()
    paginator = Paginator(articles, ARTICLES_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'articles': page_obj,
        'page_obj': page_obj,
        'total': total,
        'query': query,
        'selected_tags': selected_tags,
        'tag_chips': tag_chips,
        'base_qs': base_qs,
        'form': form,
        'show_modal': show_modal,
    }
    return render(request, 'articles/articles_index.html', context)


@login_required
def edit(request, pk):
    """Edita um artigo existente do usuário (RF02)."""
    article = get_object_or_404(Articles, pk=pk, user=request.user)

    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            article.tags.clear()
            form.save_tags(article)
            messages.success(request, 'Artigo atualizado com sucesso!')
            return redirect('articles-index')
        messages.error(request, 'Corrija os campos destacados e tente novamente.')
    else:
        form = ArticleForm(instance=article, initial={
            'tags': ', '.join(article.tags.values_list('name', flat=True)),
        })

    return render(request, 'articles/article_edit.html', {'form': form, 'article': article})


@login_required
@require_POST
def delete(request, pk):
    """Exclui um artigo do usuário (RF02)."""
    article = get_object_or_404(Articles, pk=pk, user=request.user)
    article.delete()
    messages.success(request, 'Artigo excluído com sucesso!')
    return redirect('articles-index')


@login_required
@require_POST
def bulk_delete(request):
    """Exclui em lote os artigos selecionados do usuário (RF02)."""
    ids = request.POST.getlist('selected')
    qs = Articles.objects.filter(pk__in=ids, user=request.user)
    count = qs.count()
    if count:
        qs.delete()
        messages.success(request, f'{count} artigo{pluralize(count)} excluído{pluralize(count)} com sucesso!')
    else:
        messages.error(request, 'Selecione ao menos um artigo para excluir.')
    return redirect('articles-index')


@login_required
def lookup_doi(request):
    """Busca metadados de um artigo na Crossref pelo DOI (RF01).

    Endpoint JSON consumido pelo modal para preenchimento automático.
    """
    try:
        data = crossref.lookup(request.GET.get('doi', ''))
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=400)
    except LookupError as exc:
        return JsonResponse({'error': str(exc)}, status=404)
    except crossref.CrossrefError as exc:
        return JsonResponse({'error': str(exc)}, status=502)
    return JsonResponse(data)
