import json
import secrets
import time
import traceback
import urllib.error
import urllib.request

from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from urllib.parse import urlencode

# Caracteres aceitos como "especiais" na senha.
SPECIAL_CHARS = set('!@#$%^&*()-_=+[]{};:,.<>?/|\\~`"\'')
OTP_TTL_SECONDS = 600  # validade do código: 10 minutos

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
    # Tags usadas por artigos: clicar nelas abre a lista de artigos; as demais
    # (só de insights) abrem o Banco de Ideias, para não cair numa lista vazia.
    article_tag_ids = set()

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
            article_tag_ids.add(str(tag.pk))
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
        # Tags de artigos vão para a lista de artigos; tags exclusivas de
        # insights vão para o Banco de Ideias, ambas já filtradas pela tag.
        list_url = 'articles-index' if tag_id in article_tag_ids else 'ideas-index'
        nodes.append({
            'id': f't:{tag_id}',
            'label': f'#{name}',
            'type': 'tag',
            'url': _filtered(list_url, tag=name),
        })

    graph = {'nodes': nodes, 'links': links}
    return render(request, 'graph.html', {'graph': graph})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('articles-index')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        # Login por e-mail: localiza a conta e autentica pelo username interno.
        user = None
        account = User.objects.filter(email__iexact=email).first() if email else None
        if account:
            user = authenticate(request, username=account.username, password=password)
        if user is not None:
            login(request, user)
            return redirect('articles-index')
        messages.error(request, 'E-mail ou senha inválidos.')
        return render(request, 'login.html', {'email': email})
    return render(request, 'login.html')


def _generate_code():
    return f'{secrets.randbelow(1000000):06d}'


def _send_via_resend(to_email, subject, text):
    """Envia e-mail pela API HTTP do Resend. Usa urllib (que respeita o proxy
    do PythonAnywhere), então funciona no plano free — ao contrário do SMTP."""
    payload = json.dumps({
        'from': settings.DEFAULT_FROM_EMAIL,
        'to': [to_email],
        'subject': subject,
        'text': text,
    }).encode('utf-8')
    request = urllib.request.Request(
        'https://api.resend.com/emails',
        data=payload,
        headers={
            'Authorization': 'Bearer ' + settings.RESEND_API_KEY,
            'Content-Type': 'application/json',
            # O Cloudflare na frente da API do Resend bloqueia o User-Agent
            # padrão do urllib (Python-urllib) com erro 1010. Definimos um
            # User-Agent comum para a requisição passar.
            'User-Agent': 'ScholarHub/1.0',
        },
        method='POST',
    )
    # urlopen levanta HTTPError em respostas 4xx/5xx; quem chama trata o erro.
    with urllib.request.urlopen(request, timeout=15) as response:
        response.read()


def _send_otp(email, code):
    subject = 'Seu código de confirmação – ScholarHub'
    text = (
        f'Olá!\n\nSeu código de confirmação do ScholarHub é: {code}\n\n'
        'Ele expira em 10 minutos. Se não foi você, ignore este e-mail.'
    )
    if settings.RESEND_API_KEY:
        _send_via_resend(email, subject, text)
    else:
        send_mail(subject, text, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('articles-index')
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        ctx = {'name': name, 'email': email}

        if not name:
            messages.error(request, 'Informe seu nome.')
        elif not email:
            messages.error(request, 'Informe um e-mail.')
        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, 'Já existe uma conta com este e-mail.')
        elif password1 != password2:
            messages.error(request, 'As senhas não coincidem.')
        elif len(password1) < 8:
            messages.error(request, 'A senha deve ter ao menos 8 caracteres.')
        elif not any(c in SPECIAL_CHARS for c in password1):
            messages.error(request, 'A senha deve conter ao menos um caractere especial.')
        else:
            code = _generate_code()
            # Guarda o cadastro pendente na sessão (senha já com hash) e só cria
            # a conta após a confirmação do código. Evita contas não verificadas.
            request.session['pending_registration'] = {
                'name': name,
                'email': email,
                'password': make_password(password1),
                'code': code,
                'expires': time.time() + OTP_TTL_SECONDS,
            }
            try:
                _send_otp(email, code)
            except Exception as e:
                del request.session['pending_registration']
                traceback.print_exc()
                if isinstance(e, urllib.error.HTTPError):
                    print('Resend HTTPError', e.code, e.read().decode(errors='replace'))
                messages.error(request, 'Não foi possível enviar o e-mail. Tente novamente mais tarde.')
                return render(request, 'register.html', ctx)
            messages.info(request, f'Enviamos um código de 6 dígitos para {email}.')
            return redirect('verify')
        return render(request, 'register.html', ctx)
    return render(request, 'register.html')


def verify_view(request):
    pending = request.session.get('pending_registration')
    if not pending:
        return redirect('register')

    if request.method == 'POST':
        # Reenvio de código.
        if request.POST.get('resend'):
            code = _generate_code()
            pending['code'] = code
            pending['expires'] = time.time() + OTP_TTL_SECONDS
            request.session['pending_registration'] = pending
            try:
                _send_otp(pending['email'], code)
                messages.info(request, 'Enviamos um novo código.')
            except Exception as e:
                traceback.print_exc()
                if isinstance(e, urllib.error.HTTPError):
                    print('Resend HTTPError', e.code, e.read().decode(errors='replace'))
                messages.error(request, 'Não foi possível reenviar o e-mail.')
            return redirect('verify')

        entered = request.POST.get('code', '').strip()
        if time.time() > pending['expires']:
            messages.error(request, 'O código expirou. Solicite um novo.')
        elif entered == pending['code']:
            # Cria a conta: username = e-mail (login por e-mail), nome no
            # first_name. A senha já está com hash, então atribuímos direto.
            user = User(
                username=pending['email'],
                email=pending['email'],
                first_name=pending['name'],
            )
            user.password = pending['password']
            user.save()
            del request.session['pending_registration']
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Conta confirmada! Bem-vindo(a) ao ScholarHub.')
            return redirect('articles-index')
        else:
            messages.error(request, 'Código inválido. Tente novamente.')

    return render(request, 'verify.html', {'email': pending['email']})


def forgot_password_view(request):
    """Pede o e-mail e envia um código OTP para redefinição de senha."""
    if request.user.is_authenticated:
        return redirect('articles-index')
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        account = User.objects.filter(email__iexact=email).first() if email else None
        if not account:
            messages.error(request, 'Não encontramos uma conta com este e-mail.')
            return render(request, 'forgot_password.html', {'email': email})

        code = _generate_code()
        # Guarda a redefinição pendente na sessão; a senha só muda após a
        # confirmação do código enviado por e-mail.
        request.session['pending_reset'] = {
            'email': account.email,
            'code': code,
            'expires': time.time() + OTP_TTL_SECONDS,
        }
        try:
            _send_otp(account.email, code)
        except Exception as e:
            del request.session['pending_reset']
            traceback.print_exc()
            if isinstance(e, urllib.error.HTTPError):
                print('Resend HTTPError', e.code, e.read().decode(errors='replace'))
            messages.error(request, 'Não foi possível enviar o e-mail. Tente novamente mais tarde.')
            return render(request, 'forgot_password.html', {'email': email})

        messages.info(request, f'Enviamos um código de 6 dígitos para {account.email}.')
        return redirect('reset-password')
    return render(request, 'forgot_password.html')


def reset_password_view(request):
    """Confirma o código OTP e define a nova senha."""
    pending = request.session.get('pending_reset')
    if not pending:
        return redirect('forgot-password')

    if request.method == 'POST':
        # Reenvio de código.
        if request.POST.get('resend'):
            code = _generate_code()
            pending['code'] = code
            pending['expires'] = time.time() + OTP_TTL_SECONDS
            request.session['pending_reset'] = pending
            try:
                _send_otp(pending['email'], code)
                messages.info(request, 'Enviamos um novo código.')
            except Exception as e:
                traceback.print_exc()
                if isinstance(e, urllib.error.HTTPError):
                    print('Resend HTTPError', e.code, e.read().decode(errors='replace'))
                messages.error(request, 'Não foi possível reenviar o e-mail.')
            return redirect('reset-password')

        entered = request.POST.get('code', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if time.time() > pending['expires']:
            messages.error(request, 'O código expirou. Solicite um novo.')
        elif entered != pending['code']:
            messages.error(request, 'Código inválido. Tente novamente.')
        elif password1 != password2:
            messages.error(request, 'As senhas não coincidem.')
        elif len(password1) < 8:
            messages.error(request, 'A senha deve ter ao menos 8 caracteres.')
        elif not any(c in SPECIAL_CHARS for c in password1):
            messages.error(request, 'A senha deve conter ao menos um caractere especial.')
        else:
            user = User.objects.filter(email__iexact=pending['email']).first()
            if not user:
                del request.session['pending_reset']
                messages.error(request, 'Conta não encontrada.')
                return redirect('login')
            user.set_password(password1)
            user.save()
            del request.session['pending_reset']
            messages.success(request, 'Senha redefinida! Faça login com a nova senha.')
            return redirect('login')

    return render(request, 'reset_password.html', {'email': pending['email']})


def logout_view(request):
    logout(request)
    return redirect('login')
