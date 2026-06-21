from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.template.defaultfilters import pluralize
from django.views.decorators.http import require_POST

from articles import tagfilters
from articles.models import Tag

from .forms import IdeaForm
from .models import Idea

IDEAS_PER_PAGE = 10


@login_required
def index(request):
    """Banco de Ideias: lista as ideias do usuário com busca global (RF04)
    e cadastro de nova ideia via modal (RF03)."""
    form = IdeaForm(user=request.user)
    show_modal = False

    if request.method == 'POST':
        form = IdeaForm(request.POST, user=request.user)
        if form.is_valid():
            idea = form.save(commit=False)
            idea.user = request.user
            idea.save()
            form.save_tags(idea)
            messages.success(request, 'Ideia registrada com sucesso!')
            return redirect('ideas-index')
        # Form inválido: reexibe a tela com o modal aberto e os erros.
        show_modal = True
        messages.error(request, 'Corrija os campos destacados e tente novamente.')

    query = request.GET.get('q', '').strip()
    selected_tags = tagfilters.get_selected_tags(request)
    ideas = Idea.objects.filter(user=request.user).select_related('article')

    if query:
        ideas = ideas.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(article__title__icontains=query)
            | Q(tags__name__icontains=query)
        )
    ideas = tagfilters.filter_by_tags(ideas, selected_tags).distinct()

    # Tags disponíveis para o filtro (apenas as usadas pelas ideias do usuário).
    available_tags = Tag.objects.filter(ideas__user=request.user).distinct().order_by('name')
    tag_chips, base_qs = tagfilters.build_tag_chips(available_tags, selected_tags, query)

    total = ideas.count()
    paginator = Paginator(ideas, IDEAS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'ideas': page_obj,
        'page_obj': page_obj,
        'total': total,
        'query': query,
        'selected_tags': selected_tags,
        'tag_chips': tag_chips,
        'base_qs': base_qs,
        'form': form,
        'show_modal': show_modal,
    }
    return render(request, 'ideas/ideas_index.html', context)


@login_required
def edit(request, pk):
    """Edita uma ideia existente do usuário (RF03)."""
    idea = get_object_or_404(Idea, pk=pk, user=request.user)

    if request.method == 'POST':
        form = IdeaForm(request.POST, instance=idea, user=request.user)
        if form.is_valid():
            form.save()
            idea.tags.clear()
            form.save_tags(idea)
            messages.success(request, 'Ideia atualizada com sucesso!')
            return redirect('ideas-index')
        messages.error(request, 'Corrija os campos destacados e tente novamente.')
    else:
        form = IdeaForm(instance=idea, user=request.user, initial={
            'tags': ', '.join(idea.tags.values_list('name', flat=True)),
        })

    return render(request, 'ideas/idea_edit.html', {'form': form, 'idea': idea})


@login_required
@require_POST
def delete(request, pk):
    """Exclui uma ideia do usuário (RF03)."""
    idea = get_object_or_404(Idea, pk=pk, user=request.user)
    idea.delete()
    messages.success(request, 'Ideia excluída com sucesso!')
    return redirect('ideas-index')


@login_required
@require_POST
def bulk_delete(request):
    """Exclui em lote as ideias selecionadas do usuário (RF03)."""
    ids = request.POST.getlist('selected')
    qs = Idea.objects.filter(pk__in=ids, user=request.user)
    count = qs.count()
    if count:
        qs.delete()
        messages.success(request, f'{count} ideia{pluralize(count)} excluída{pluralize(count)} com sucesso!')
    else:
        messages.error(request, 'Selecione ao menos uma ideia para excluir.')
    return redirect('ideas-index')
