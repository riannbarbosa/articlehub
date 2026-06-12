from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from .models import Articles


@login_required
def index(request):
    """Tela principal: lista os artigos do usuário com busca global (RF04)."""
    query = request.GET.get('q', '').strip()
    articles = Articles.objects.filter(user=request.user)

    if query:
        articles = articles.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(annotation__content__icontains=query)
            | Q(tags__name__icontains=query)
        ).distinct()

    context = {
        'articles': articles,
        'query': query,
    }
    return render(request, 'articles/articles_index.html', context)
