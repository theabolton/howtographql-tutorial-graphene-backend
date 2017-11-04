import binascii
import os

from django.db import models


# The How to GraphQL graphene back end tutorial
# (https://www.howtographql.com/graphql-python/4-authentication/) extends
# Django's user and authentication system. It's not easily possible to use
# Django's authentication system without being stuck with a user name field of
# 'username', rather than 'name' as the front-end tutorial expects. So here is
# a simple User model, just capable enough to support the tutorial, but every
# bit as naïve as the tutorial regarding security....

def new_token():
    return binascii.b2a_hex(os.urandom(32)).decode()


class UserModel(models.Model):
    name = models.CharField(max_length=150)
    password = models.CharField(max_length=128)
    email = models.EmailField(unique=True)
    token = models.CharField(max_length=64, default=new_token)
