from django.db import models

class LinkModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.TextField(null=True, blank=True)
    url = models.URLField()
