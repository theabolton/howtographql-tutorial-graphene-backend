# howtographql-graphene-tutorial-fixed -- users/tests.py
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

from django.test import TestCase

import graphene
from graphene.relay import Node

from hackernews.schema import Mutation, Query
from hackernews.utils import format_graphql_errors, quiet_graphql, unquiet_graphql
from .models import UserModel
from .schema import get_user_from_auth_token


# ========== graphql-core exception reporting during tests ==========

# graphql-core (2.0) is rather obnoxious about reporting exceptions, nearly all of which are
# expected ones, so hush it up during tests. Use format_graphql_errors() to report the information
# when and where you want.
def setUpModule():
    quiet_graphql()

def tearDownModule():
    unquiet_graphql()


# ========== utility function ==========

def create_test_user(name=None, password=None, email=None):
    user = UserModel.objects.create(
        name=name or 'Test User',
        password=password or 'abc123',
        email=email or 'test@user.com'
    )
    return user


# ========== user authentication token tests ==========

class UserAuthTokenTests(TestCase):
    def test_token_creation(self):
        """ensure token is created for new UserModel"""
        user = create_test_user()
        self.assertIsInstance(user.token, str)
        self.assertRegex(user.token, r'^[0-9a-f]{40,}')

    def test_token_uniqueness(self):
        """check that users are not given the same token"""
        token1 = create_test_user().token
        user2 = UserModel(name='Test User 2', password='abc123', email='test2@user.com')
        user2.save()
        token2 = user2.token
        self.assertNotEqual(token1, token2)


class GetUserTests(TestCase):
    def test_get_user_token_missing_or_invalid(self):
        """get_user_from_auth_token() with no or invalid HTTP_AUTHORIZATION header should
        return None
        """
        create_test_user()
        class AuthEmpty(object):
            META = {}
        self.assertIsNone(get_user_from_auth_token(AuthEmpty))
        class AuthInvalid(object):
            META = {'HTTP_AUTHORIZATION': 'ArgleBargle'}
        self.assertIsNone(get_user_from_auth_token(AuthInvalid))

    def test_get_user_token_valid(self):
        """get_user_from_auth_token() with valid HTTP_AUTHORIZATION header should return user"""
        user = create_test_user()
        class AuthValid(object):
            META = {'HTTP_AUTHORIZATION': 'Bearer {}'.format(user.token)}
        self.assertEqual(get_user_from_auth_token(AuthValid), user)

    def test_get_user_token_wrong(self):
        """get_user_from_auth_token() with valid HTTP_AUTHORIZATION header but invalid token
        should raise
        """
        user = create_test_user()
        class AuthWrong(object):
            META = {'HTTP_AUTHORIZATION': 'Bearer AbDbAbDbAbDbA'}
        with self.assertRaises(Exception):
            get_user_from_auth_token(AuthWrong)


# ========== Relay Node tests ==========

class RelayNodeTests(TestCase):
    """Test that model nodes can be retreived via the Relay Node interface."""
    def test_node_for_user(self):
        user = create_test_user()
        user_gid = Node.to_global_id('User', user.pk)
        query = '''
          query {
            node(id: "%s") {
              id
              ...on User {
                name
              }
            }
          }
        ''' % user_gid
        expected = {
          'node': {
            'id': user_gid,
            'name': user.name,
          }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))


# ========== createUser mutation tests ==========

class CreateUserTests(TestCase):
    def setUp(self):
        self.query = '''
          mutation CreateUserMutation($createUserInput: SignupUserInput!) {
            createUser(input: $createUserInput) {
              user { name }
            }
          }
        '''
        self.variables = {
            'createUserInput': {
                'name': 'Jim Kirk',
                'authProvider': {
                    'email': {
                        'email': 'kirk@example.com',
                        'password': 'abc123',
                    }
                },
            }
        }
        self.expected = {
            'createUser': {
                'user': {
                    'name': 'Jim Kirk',
                }
            }
        }
        self.schema = graphene.Schema(query=Query, mutation=Mutation)

    def test_create_user(self):
        """sucessfully create a user"""
        result = self.schema.execute(self.query, variable_values=self.variables)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, self.expected,
                         msg='\n'+repr(self.expected)+'\n'+repr(result.data))
        # check that the user was created properly
        user = UserModel.objects.get(name=result.data['createUser']['user']['name'])
        self.assertEqual(user.name, 'Jim Kirk')
        self.assertEqual(user.email, 'kirk@example.com')
        self.assertEqual(user.password, 'abc123')
        self.assertRegex(user.token, r'^[0-9a-f]{40,}')

    def test_create_user_duplicate(self):
        """should not be able to create two users with the same email"""
        result = self.schema.execute(self.query, variable_values=self.variables)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, self.expected,
                         msg='\n'+repr(self.expected)+'\n'+repr(result.data))
        # now try to create a second one
        self.variables['createUserInput']['name'] = 'Just Spock to Humans'
        auth = self.variables['createUserInput']['authProvider']['email']
        auth['password'] = '26327790.8685354193060378'
        # -- email address stays the same
        result = self.schema.execute(self.query, variable_values=self.variables)
        self.assertIsNotNone(result.errors,
                             msg='Creating user with duplicate email should have failed')
        self.assertIn('user with that email address already exists', repr(result.errors))
        expected = { 'createUser': None } # empty result
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))


# ========== signUser mutation tests ==========

class SigninUserTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.query = '''
          mutation SigninUserMutation($signinUserInput: SigninUserInput!) {
            signinUser(input: $signinUserInput) {
              token
              user { name }
            }
          }
        '''
        self.schema = graphene.Schema(query=Query, mutation=Mutation)

    def test_signin_user(self):
        """normal user sign-in"""
        variables = {
            'signinUserInput': {
                'email': {
                    'email': self.user.email,
                    'password': self.user.password,
                }
            }
        }
        expected = {
            'signinUser': {
                'token': 'REDACTED',
                'user': {
                    'name': self.user.name,
                }
            }
        }
        result = self.schema.execute(self.query, variable_values=variables)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        try:
            token = result.data['signinUser']['token']
            result.data['signinUser']['token'] = 'REDACTED'
        except KeyError:
            raise Exception('malformed mutation result')
        self.assertRegex(token, r'^[0-9a-f]{40,}')
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_signin_user_not_found(self):
        """unsuccessful sign-in: user not found"""
        variables = {
            'signinUserInput': {
                'email': {
                    'email': 'xxx' + self.user.email, # unknown email address
                    'password': 'irrelevant',
                }
            }
        }
        expected = {'signinUser': None} # empty result
        result = self.schema.execute(self.query, variable_values=variables)
        self.assertIsNotNone(result.errors,
                             msg='Sign-in of user with unknown email should have failed')
        self.assertIn('Invalid username or password', repr(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_signin_user_bad_password(self):
        """unsuccessful sign-in: incorrect password"""
        variables = {
            'signinUserInput': {
                'email': {
                    'email': self.user.email,
                    'password': 'xxx' + self.user.password, # incorrect password
                }
            }
        }
        expected = {'signinUser': None} # empty result
        result = self.schema.execute(self.query, variable_values=variables)
        self.assertIsNotNone(result.errors,
                             msg='Sign-in of user with incorrect password should have failed')
        self.assertIn('Invalid username or password', repr(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))
