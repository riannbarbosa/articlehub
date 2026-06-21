import uuid
from django.conf import settings
from django.db import models

class Articles(models.Model):
    id = models.UUIDField( primary_key=True,default=uuid.uuid4, editable=False)
    title = models.CharField('Título do artigo', max_length=255)
    author = models.CharField('Autor do artigo', max_length=255)
    year = models.PositiveSmallIntegerField('Ano de publicação')
    link = models.URLField('Link do artigo')
    doi = models.CharField('DOI', max_length=255, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='articles')
    tags = models.ManyToManyField('Tag', related_name='articles', blank=True)
    
    class Quality(models.IntegerChoices):
        POOR = 1, 'Ruim'
        AVERAGE = 2, 'Médio'
        GOOD = 3, 'Bom'
        EXCELLENT = 4, 'Excelente'
    quality = models.IntegerField('Qualidade do artigo', null=True, blank=True, choices=Quality.choices)
    
    created_at = models.DateTimeField('Data de criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de atualização', auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Artigo'
        verbose_name_plural = 'Artigos'

    def __str__(self):
        return f'{self.title} ({self.year}) - {self.get_quality_display() if self.quality else "Sem avaliação"}'
    
    
class Annotation(models.Model):
    id = models.UUIDField( primary_key=True,default=uuid.uuid4, editable=False)
    content = models.TextField('Conteúdo da anotação')
    article = models.OneToOneField('Articles', on_delete=models.CASCADE, related_name='annotation')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='annotations')
    created_at = models.DateTimeField('Data de criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de atualização', auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Annotation'
        verbose_name_plural = 'Annotations'

    def __str__(self):
        return f'Anotação para {self.article.title} - {self.created_at.strftime("%Y-%m-%d %H:%M:%S")}' 
    
class Tag(models.Model):
    id = models.UUIDField( primary_key=True,default=uuid.uuid4, editable=False)
    name = models.CharField('Nome da tag', max_length=50)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.name