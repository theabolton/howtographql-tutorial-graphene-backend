# howtographql-graphene-tutorial-fixed -- users/schema.py
#
# Copyright © 2017 Sean Bolton.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import graphene
from graphene import relay
from graphene.relay import Node
from graphene_django import DjangoObjectType

from users.models import UserModel


def get_user_from_auth_token(context):
    # attempt to get the user from an authorization token in the HTTP headers
    auth = context.META.get('HTTP_AUTHORIZATION', None)
    if not auth or not auth.startswith('Bearer '):
        return None
    token = auth[7:]
    try:
        return UserModel.objects.get(token=token)
    except:
        raise Exception('User not found!')


class User(DjangoObjectType):
    class Meta:
        model = UserModel
        interfaces = (Node, )


class Query(object):
    pass


class AUTH_PROVIDER_EMAIL(graphene.InputObjectType):
    email = graphene.String(required=True)
    password = graphene.String(required=True)


class AuthProviderSignupData(graphene.InputObjectType):
    email = graphene.InputField(AUTH_PROVIDER_EMAIL, required=True)


class CreateUser(relay.ClientIDMutation):
    # This is as simplistic as the front-end tutorial's authentication model, and does not try to
    # e.g. cryptographically hash the password before storing it, or verify the user's email.
    # mutation CreateUserMutation($createUserInput: SignupUserInput!) {
    #   createUser(input: $createUserInput) {
    #     user { id }
    #   }
    # }
    # example variables:
    #   input: {
    #     name: "Foo Bar",
    #     authProvider: {
    #       email: {
    #         email: "foo@bar.com",
    #         password: "abc123",
    #       }
    #     },
    #     clientMutationId: "",
    #   }

    user = graphene.Field(User)

    # We need to rename the input type from the default 'CreateUserInput' to the 'SignupUserInput'
    # that the front-end expects. Graphene 2.0 has a bug that makes it so that this straightforward
    # approach doesn't work:
    #     class Input:
    #         class Meta:
    #             name = 'SignupUserInput'
    # (The bug results in graphene/utils/subclass_with_meta.py, line 28, 'delattr(cls, "Meta")'
    # raising an AttributeError.)
    # Instead, we do this:
    class Input(graphene.types.base.BaseType):
        def __init_subclass__(cls, *args, **kwargs):
            # add Meta in a way that can be delattr()ed
            cls.Meta = { 'name': 'SignupUserInput' }
            super().__init_subclass__(**kwargs)

        name = graphene.String(required=True)
        auth_provider = graphene.InputField(AuthProviderSignupData, required=True)

    # Normally, it is convenient to destructure the inputs here like this:
    #    def mutate_and_get_payload(cls, root, info, name, auth_provider, client_mutation_id=None):
    # but because AuthProviderSignupData has an 'email' field of type AUTH_PROVIDER_EMAIL, which
    # also has a field named 'email', the destructuring gets messed up, resulting in graphene
    # complaining about unknown fields. In these cases, use '**' to capture the inputs instead.
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        name = input.get('name')
        auth = input.get('auth_provider').get('email')
        email = auth.get('email')
        password = auth.get('password')
        if UserModel.objects.filter(email=email).exists():
            raise Exception('A user with that email address already exists!')
        user = UserModel(
            name=name,
            email=email,
            password=password,
        )
        user.save()
        return CreateUser(user=user)


class SigninUser(relay.ClientIDMutation):
    # mutation SigninUserMutation($signinUserInput: SigninUserInput!) {
    #   signinUser(input: $signinUserInput) {
    #     token
    #     user { id }
    #   }
    # }
    # example variables: email: { email: "foo@bar.com", password: "abc123" }

    token = graphene.String()
    user = graphene.Field(User)

    class Input:
        email = graphene.InputField(AUTH_PROVIDER_EMAIL, required=True)

    # See the note about using '**input' vs. destructuring the input fields in CreateUser, above.
    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        email = input.get('email').get('email')
        password = input.get('email').get('password')
        try:
            user = UserModel.objects.get(email=email)
            assert user.password == password
        except Exception:
            raise Exception('Invalid username or password!')

        return SigninUser(token=user.token, user=user)


class Mutation(object):
    create_user = CreateUser.Field()
    signin_user = SigninUser.Field()
