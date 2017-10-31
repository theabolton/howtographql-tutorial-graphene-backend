from django.contrib import admin

from .models import LinkModel

admin.site.site_header = 'How to GraphQL graphql-python Tutorial Administration'
admin.site.site_title = 'graphql-python site admin'

admin.site.register(LinkModel)
