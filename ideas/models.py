import uuid
from django.conf import settings
from django.db import models


class Idea(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField('Título da ideia', max_length=255)
    content = models.TextField('Descrição da ideia')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ideas')
    article = models.ForeignKey('articles.Articles', on_delete=models.SET_NULL, null=True, blank=True, related_name='ideas')
    tags = models.ManyToManyField('articles.Tag', related_name='ideas', blank=True)
    created_at = models.DateTimeField('Data de criação', auto_now_add=True)
    updated_at = models.DateTimeField('Data de atualização', auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ideia'
        verbose_name_plural = 'Ideias'

    def __str__(self):
        return self.title
