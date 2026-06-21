from django import forms

from .models import Annotation, Articles, Tag


class ArticleForm(forms.ModelForm):
    """Formulário de cadastro de artigo (RF01).

    O campo de tags é exposto como texto separado por vírgula; a relação
    ManyToMany é resolvida na view, criando as Tags que ainda não existirem.
    """

    tags = forms.CharField(
        label='Tags',
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'machine learning, nlp (separadas por vírgula)',
        }),
    )

    class Meta:
        model = Articles
        fields = ['doi', 'title', 'author', 'year', 'link', 'quality']
        widgets = {
            'doi': forms.TextInput(attrs={'placeholder': '10.1000/xyz123'}),
            'title': forms.TextInput(attrs={'placeholder': 'Título do artigo'}),
            'author': forms.TextInput(attrs={'placeholder': 'Autor do artigo'}),
            'year': forms.NumberInput(attrs={'placeholder': 'Ano', 'min': 0}),
            'link': forms.URLInput(attrs={'placeholder': 'https://...'}),
        }

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

    def save_tags(self, article):
        """Cria/recupera as Tags e associa ao artigo já persistido."""
        for name in self.cleaned_data['tags']:
            tag, _ = Tag.objects.get_or_create(name=name)
            article.tags.add(tag)


class AnnotationForm(forms.ModelForm):
    """Editor de fichamento/resumo de um artigo (RF02).

    Expõe apenas o conteúdo; o vínculo obrigatório com o artigo (RN01) e o
    dono são definidos na view.
    """

    class Meta:
        model = Annotation
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'placeholder': 'Escreva o fichamento: resumo, citações relevantes e comentários críticos...',
                'rows': 16,
            }),
        }
        labels = {'content': 'Fichamento'}
