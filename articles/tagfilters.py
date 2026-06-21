"""Filtro por tags reutilizado nas telas de Artigos e Ideias (RF04).

As tags selecionadas chegam como parâmetros `?tag=` repetidos na querystring e
são combinadas em E (o item precisa conter todas as tags marcadas), podendo se
somar à busca textual `?q=`.
"""
from urllib.parse import urlencode


def get_selected_tags(request):
    """Lista de nomes de tags marcados na querystring, sem vazios."""
    return [name for name in request.GET.getlist('tag') if name.strip()]


def filter_by_tags(queryset, selected_tags):
    """Restringe o queryset aos itens que possuem todas as tags marcadas."""
    for name in selected_tags:
        queryset = queryset.filter(tags__name=name)
    return queryset


def build_tag_chips(available_tags, selected_tags, query):
    """Monta os chips de filtro e a querystring base (busca + tags ativas).

    Cada chip carrega a querystring que liga/desliga aquela tag, preservando a
    busca textual e as demais tags já marcadas. `base_qs` é usada na paginação
    para manter os filtros ativos ao trocar de página.
    """
    chips = []
    for tag in available_tags:
        active = tag.name in selected_tags
        if active:
            remaining = [name for name in selected_tags if name != tag.name]
        else:
            remaining = selected_tags + [tag.name]
        params = ([('q', query)] if query else []) + [('tag', name) for name in remaining]
        chips.append({'name': tag.name, 'active': active, 'qs': urlencode(params)})

    base_params = ([('q', query)] if query else []) + [('tag', name) for name in selected_tags]
    return chips, urlencode(base_params)
