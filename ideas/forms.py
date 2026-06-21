from django import forms

from articles.models import Articles, Tag

from .models import Idea


class IdeaForm(forms.ModelForm):
    """Formulário do Banco de Ideias (RF03).

    O vínculo com um artigo é opcional (RN02) e o campo de tags é exposto como
    texto separado por vírgula, reaproveitando o mesmo modelo `Tag` dos artigos;
    a relação ManyToMany é resolvida na view, criando as Tags inexistentes.
    """

    tags = forms.CharField(
        label='Tags',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'insight, dúvida (separadas por vírgula)',
        }),
    )

    class Meta:
        model = Idea
        fields = ['title', 'article', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Título da ideia'}),
            'content': forms.Textarea(attrs={
                'placeholder': 'Descreva o insight, conexão ou anotação rápida...',
                'rows': 5,
            }),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # A ideia pode existir sem artigo (RN02); restringe a escolha aos
        # artigos do próprio usuário.
        article = self.fields['article']
        article.required = False
        article.empty_label = 'Nenhum artigo (ideia solta)'
        # Rótulo enxuto (título + ano) para não estourar a largura do select.
        article.label_from_instance = lambda obj: f'{obj.title} ({obj.year})'
        if user is not None:
            article.queryset = Articles.objects.filter(user=user)

    def clean_tags(self):
        """Normaliza a string de tags numa lista de nomes únicos e não vazios."""
        raw = self.cleaned_data.get('tags', '')
        names, seen = [], set()
        for name in raw.split(','):
            name = name.strip()
            key = name.lower()
            if name and key not in seen:
                seen.add(key)
                names.append(name)
        return names

    def save_tags(self, idea):
        """Cria/recupera as Tags e associa à ideia já persistida."""
        for name in self.cleaned_data['tags']:
            tag, _ = Tag.objects.get_or_create(name=name)
            idea.tags.add(tag)
