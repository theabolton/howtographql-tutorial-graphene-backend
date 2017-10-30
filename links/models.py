from django.db import models

class Link(models.Model):
    description = models.TextField(null=True, blank=True)
    url = models.URLField()
