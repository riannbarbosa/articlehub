"""Cliente mínimo da API pública da Crossref (https://api.crossref.org).

Usa apenas a biblioteca padrão para não adicionar dependências. Dado um DOI,
retorna os metadados do artigo já normalizados para os campos do modelo.
"""

import json
import urllib.error
import urllib.parse
import urllib.request

API_URL = 'https://api.crossref.org/works/'
# A Crossref pede um User-Agent identificável (com e-mail de contato) para o
# "polite pool", que oferece melhor confiabilidade.
USER_AGENT = 'ScholarHub/1.0 (mailto:riannbarbosa5@gmail.com)'
TIMEOUT = 8


class CrossrefError(Exception):
    """Falha ao consultar a Crossref (rede, timeout ou resposta inválida)."""


def _format_authors(authors):
    """Transforma a lista de autores da Crossref em 'Nome Sobrenome, ...'."""
    names = []
    for author in authors or []:
        full = ' '.join(p for p in (author.get('given'), author.get('family')) if p)
        names.append(full or author.get('name', ''))
    return ', '.join(n for n in names if n)


def _extract_year(message):
    """Pega o ano a partir do primeiro campo de data disponível."""
    for key in ('published', 'published-print', 'published-online', 'issued', 'created'):
        parts = (message.get(key) or {}).get('date-parts') or []
        if parts and parts[0] and parts[0][0]:
            return parts[0][0]
    return None


def lookup(doi):
    """Consulta um DOI e devolve um dict com title, author, year, link e doi.

    Levanta ValueError se o DOI for vazio, LookupError se não existir (404) e
    CrossrefError para outras falhas de rede/resposta.
    """
    doi = (doi or '').strip()
    # Aceita tanto o DOI puro quanto uma URL https://doi.org/<doi>.
    for prefix in ('https://doi.org/', 'http://doi.org/', 'doi.org/'):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix):]
            break
    if not doi:
        raise ValueError('DOI vazio.')

    url = API_URL + urllib.parse.quote(doi, safe='')
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise LookupError('DOI não encontrado na Crossref.')
        raise CrossrefError('A Crossref retornou erro %s.' % exc.code)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise CrossrefError('Não foi possível consultar a Crossref: %s' % exc)

    message = payload.get('message', {})
    titles = message.get('title') or []
    year = _extract_year(message)
    return {
        'doi': message.get('DOI', doi),
        'title': titles[0] if titles else '',
        'author': _format_authors(message.get('author')),
        'year': year,
        'link': message.get('URL', 'https://doi.org/' + doi),
    }
