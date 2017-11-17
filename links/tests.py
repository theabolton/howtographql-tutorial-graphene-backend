# howtographql-graphene-tutorial-fixed -- links/tests.py
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
from links.models import LinkModel, VoteModel
from users.tests import create_test_user


# ========== graphql-core exception reporting during tests ==========

# graphql-core (2.0) is rather obnoxious about reporting exceptions, nearly all of which are
# expected ones, so hush it up during tests. Use format_graphql_errors() to report the information
# when and where you want.
def setUpModule():
    quiet_graphql()

def tearDownModule():
    unquiet_graphql()


# ========== GraphQL schema general tests ==========

class RootTests(TestCase):
    def test_root_query(self):
        """Make sure the root query is 'Query'.

        This test is pretty redundant, given that every other query in this file will fail if this
        is not the case, but it's a nice simple example of testing query execution.
        """
        query = '''
          query RootQueryQuery {
            __schema {
              queryType {
                name  # returns the type of the root query
              }
            }
          }
        '''
        expected = {
            '__schema': {
                'queryType': {
                    'name': 'Query'
                }
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)


class ViewerTests(TestCase):
    def test_viewer_schema(self):
        """Check the Viewer type schema contains the fields we need."""
        query = '''
          query ViewerSchemaTest {
            __type(name: "Viewer") {
              name
              fields {
                name
                type {
                  name
                  kind
                  ofType {
                    name
                  }
                }
              }
            }
          }
        '''
        expected = {
            '__type': {
                'name': 'Viewer',
                'fields': [
                    {
                        'name': 'id',
                        'type': {
                            'name': None,
                            'kind': 'NON_NULL',
                            'ofType': {
                                'name': 'ID',
                            }
                        }
                    },
                    {
                        'name': 'allLinks',
                        'type': {
                            'name': 'LinkConnection',
                            'kind': 'OBJECT',
                            'ofType': None,
                        }
                    },
                    {
                        'name': 'allVotes',
                        'type': {
                            'name': 'VoteConnection',
                            'kind': 'OBJECT',
                            'ofType': None,
                        }
                    },
                ]
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        # Check that the fields we need are there, but don't fail on extra fields.
        NEEDED_FIELDS = ('id', 'allLinks', 'allVotes')
        result.data['__type']['fields'] = list(filter(
            lambda f: f['name'] in NEEDED_FIELDS,
            result.data['__type']['fields']
        ))
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)


# ========== Relay Node tests ==========

class RelayNodeTests(TestCase):
    """Test that model nodes can be retreived via the Relay Node interface."""
    def test_node_for_link(self):
        link = LinkModel.objects.create(description='Test', url='http://a.com')
        link_gid = Node.to_global_id('Link', link.pk)
        query = '''
          query {
            node(id: "%s") {
              id
              ...on Link {
                url
              }
            }
          }
        ''' % link_gid
        expected = {
          'node': {
            'id': link_gid,
            'url': 'http://a.com',
          }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_node_for_vote(self):
        link = LinkModel.objects.create(description='Test', url='http://a.com')
        user = create_test_user()
        vote = VoteModel.objects.create(link_id=link.pk, user_id=user.pk)
        vote_gid = Node.to_global_id('Vote', vote.pk)
        query = '''
          query {
            node(id: "%s") {
              id
              ...on Vote {
                link {
                  url
                }
              }
            }
          }
        ''' % vote_gid
        expected = {
          'node': {
            'id': vote_gid,
            'link': {
              'url': 'http://a.com',
            }
          }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_node_for_viewer(self):
        query = '''
          query {
            viewer {
              id
            }
          }
        '''
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        viewer_gid = result.data['viewer']['id']
        query = '''
          query {
            node(id: "%s") {
              id
            }
          }
        ''' % viewer_gid
        expected = {
          'node': {
            'id': viewer_gid,
          }
        }
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))


# ========== allLinks query tests ==========

def create_Link_orderBy_test_data():
    """Create test data for LinkConnection orderBy tests. Create three links,
    with description, url, and created_at each having a different sort order."""
    import datetime
    import pytz
    def dt(epoch):
        return datetime.datetime.fromtimestamp(epoch).replace(tzinfo=pytz.utc)
    link = LinkModel(description='Description C', url='http://a.com')
    link.save()  # give 'auto_now_add' a chance to do its thing
    link.created_at = dt(1000000000) # new time stamp, least recent
    link.save()
    link = LinkModel(description='Description B', url='http://b.com')
    link.save()
    link.created_at = dt(1000000400) # most recent
    link.save()
    link = LinkModel(description='Description A', url='http://c.com')
    link.save()
    link.created_at = dt(1000000200)
    link.save()


class LinkTests(TestCase):
    def test_all_links(self):
        link = LinkModel(description='Description', url='http://')
        link.save()
        query = '''
          query AllLinksTest {
            viewer {
              allLinks {
                edges {
                  node {
                    id
                    description
                    url
                  }
                }
              }
            }
          }
        '''
        expected = {
            'viewer': {
                'allLinks': {
                    'edges': [
                        {
                            'node': {
                                'id': 'TGluazox',
                                'description': 'Description',
                                'url': 'http://',
                            }
                        }
                    ]
                }
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)

    def test_all_links_ordered_by(self):
        create_Link_orderBy_test_data()
        # descending order of creation: b.com, c.com, a.com
        query = '''
          query AllLinksTest {
            viewer {
              allLinks(orderBy: createdAt_DESC) {
                edges {
                  node {
                    url
                  }
                }
              }
            }
          }
        '''
        expected = {
            'viewer': {
                'allLinks': {
                    'edges': [
                        { 'node': { 'url': 'http://b.com' } },
                        { 'node': { 'url': 'http://c.com' } },
                        { 'node': { 'url': 'http://a.com' } },
                    ]
                }
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)
        # ascending order on description: c.com, b.com, a.com
        query = '''
          query AllLinksTest {
            viewer {
              allLinks(orderBy: description_ASC) {
                edges {
                  node {
                    url
                  }
                }
              }
            }
          }
        '''
        expected = {
            'viewer': {
                'allLinks': {
                    'edges': [
                        { 'node': { 'url': 'http://c.com' } },
                        { 'node': { 'url': 'http://b.com' } },
                        { 'node': { 'url': 'http://a.com' } },
                    ]
                }
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)

    def test_all_links_pagination(self):
        """Make sure that pagination still works on the custom LinkConnection."""
        create_Link_orderBy_test_data()
        # retrieve the first two links, in url order, plus a cursor for the next page
        query = '''
          query AllLinksTest {
            viewer {
              allLinks(orderBy: url_ASC, first: 2) {
                edges {
                  node {
                    url
                  }
                }
                pageInfo {
                  endCursor
                }
              }
            }
          }
        '''
        expected = {
            'viewer': {
                'allLinks': {
                    'edges': [
                        { 'node': { 'url': 'http://a.com' } },
                        { 'node': { 'url': 'http://b.com' } },
                    ],
                    'pageInfo': {
                        'endCursor': 'REDACTED',
                    }
                }
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        # save cursor, and remove it from results (don't depend on cursor representation)
        cursor = result.data['viewer']['allLinks']['pageInfo']['endCursor']
        result.data['viewer']['allLinks']['pageInfo']['endCursor'] = 'REDACTED'
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)
        # get next page of results
        query = ('''
          query AllLinksTest {
            viewer {
              allLinks(orderBy: url_ASC, first: 1, after: "''' +
          cursor +
              '''") {
                edges {
                  node {
                    url
                  }
                }
              }
            }
          }
        ''')
        expected = {
            'viewer': {
                'allLinks': {
                    'edges': [
                        { 'node': { 'url': 'http://c.com' } },
                    ],
                }
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)


# ========== createLink mutation tests ==========

class CreateLinkBasicTest(TestCase):
    def test_create_link(self):
        """Test link creation without user information (for early in the tutorial)."""
        query = '''
          mutation CreateLinkMutation($input: CreateLinkInput!) {
            createLink(input: $input) {
              link {
                url
                description
              }
              clientMutationId
            }
          }
        '''
        variables = {
            'input': {
                'description': 'Description',
                'url': 'http://example.com',
                'clientMutationId': 'give_this_back_to_me',
            }
        }
        class Context(object):
            META = {}
        expected = {
            'createLink': {
                'link': {
                    'description': 'Description',
                    'url': 'http://example.com',
                },
                'clientMutationId': 'give_this_back_to_me',
            }
        }
        schema = graphene.Schema(query=Query, mutation=Mutation)
        result = schema.execute(query, variable_values=variables, context_value=Context)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))
        # check that the link was created properly
        link = LinkModel.objects.get(description='Description')
        self.assertEqual(link.description, 'Description')
        self.assertEqual(link.url, 'http://example.com')


class CreateLinkTests(TestCase):
    def setUp(self):
        self.user = create_test_user()
        self.user_gid = Node.to_global_id('User', self.user.pk)
        self.query = '''
          mutation CreateLinkMutation($input: CreateLinkInput!) {
            createLink(input: $input) {
              link {
                url
                description
                postedBy {
                  id
                }
              }
              clientMutationId
            }
          }
        '''
        self.schema = graphene.Schema(query=Query, mutation=Mutation)

    @staticmethod
    def variables(gid):
        var = {
          'input': {
            'description': 'Description',
            'url': 'http://example.com',
            'clientMutationId': 'give_this_back_to_me',
          }
        }
        if gid:
            var['input']['postedById'] = gid
        return var

    def context_with_token(self):
        class Auth(object):
            META = {'HTTP_AUTHORIZATION': 'Bearer {}'.format(self.user.token)}
        return Auth

    @staticmethod
    def context_without_token():
        class Auth(object):
            META = {}
        return Auth

    def expected(self, with_id=True):
        return {
          'createLink': {
            'link': {
              'description': 'Description',
              'url': 'http://example.com',
              'postedBy': with_id and { 'id': self.user_gid } or None
            },
            'clientMutationId': 'give_this_back_to_me',
          }
        }

    def test_create_link_with_user_both(self):
        """createLink with both user auth token and postedById"""
        result = self.schema.execute(self.query, variable_values=self.variables(self.user_gid),
                                     context_value=self.context_with_token())
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        expected = self.expected()
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_create_link_with_only_token(self):
        """createLink with user auth token but not postedById"""
        result = self.schema.execute(self.query, variable_values=self.variables(None),
                                     context_value=self.context_with_token())
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        expected = self.expected()
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_create_link_with_only_postedById(self):
        """createLink with postedById but not user auth token, should not succeed"""
        result = self.schema.execute(self.query, variable_values=self.variables(self.user_gid),
                                     context_value=self.context_without_token())
        self.assertIsNotNone(result.errors,
                             msg='createLink should have failed: no auth token, yes postedById')
        self.assertIn('Only logged-in users may create links', repr(result.errors))
        expected = { 'createLink': None } # empty result
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_create_link_with_neither(self):
        """createLink with neither user auth token nor postedById"""
        result = self.schema.execute(self.query, variable_values=self.variables(None),
                                     context_value=self.context_without_token())
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        expected = self.expected(with_id=False)
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_create_link_with_mismatch(self):
        """createLink with mismatched user auth token and postedById, should not succeed"""
        result = self.schema.execute(self.query, variable_values=self.variables(' invalid base64 '),
                                     context_value=self.context_with_token())
        self.assertIsNotNone(result.errors,
                             msg='createLink should have failed: mismatched auth token and postedById')
        self.assertIn('postedById does not match user ID', repr(result.errors))
        expected = { 'createLink': None } # empty result
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))


# ========== Vote query tests ==========

class VotesOnLinkTests(TestCase):
    def test_votes_count_on_link_test(self):
        """test count field on votes field on Link type"""
        # first link will have one vote, last link will have two
        create_Link_orderBy_test_data() # creates more than one link
        user = create_test_user()
        first_link_id = None
        for link in LinkModel.objects.all():
            vote = VoteModel.objects.create(link_id=link.pk, user_id=user.pk)
            # save these for below
            first_link_id = first_link_id or link.pk
            last_link_id = link.pk
        user2 = create_test_user(name='Another User', password='zyz987', email='ano@user.com')
        VoteModel.objects.create(link_id=last_link_id, user_id=user2.pk)
        # check vote counts
        first_link_gid = Node.to_global_id('Link', first_link_id)
        last_link_gid = Node.to_global_id('Link', last_link_id)
        query = '''
          query VotesOnLinkTest($linkId: ID!) {
            node(id: $linkId) {
              ... on Link {
                votes {
                  count
                }
              }
            }
          }
        '''
        variables = {
            'linkId': first_link_gid,
        }
        expected = {
            'node': {
              'votes': {
                'count': 1,
              }
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query, variable_values=variables)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))
        variables['linkId'] = last_link_gid
        expected['node']['votes']['count'] = 2
        result = schema.execute(query, variable_values=variables)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))


class AdHocCheckVoteQueryTests(TestCase):
    def test_ad_hoc_check_vote_query(self):
        """As of 11/4/2017, the tutorial contains an query done outside Relay, to check whether a
        vote already exists. (On the client side? Really? Ask forgiveness rather than permisson,
        and save a round trip.) The query is done using a private API function
        (relay.environment._network.fetch) that, sure enough, went away in recent versions of Relay.
        Test that that query works (for older Relay versions, and in the event the tutorial is fixed
        for newer versions.)
        """
        create_Link_orderBy_test_data() # creates more than one link
        user = create_test_user()
        user_gid = Node.to_global_id('User', user.pk)
        user2 = create_test_user(name='Another User', password='zyz987', email='ano@user.com')
        # create multiple votes
        for link in LinkModel.objects.all():
            last_vote = VoteModel.objects.create(link_id=link.pk, user_id=user.pk)
            VoteModel.objects.create(link_id=link.pk, user_id=user2.pk)
            last_link = link
        link_gid = Node.to_global_id('Link', last_link.pk)
        vote_gid = Node.to_global_id('Vote', last_vote.pk)
        # make sure the query only returns one vote
        query = '''
          query CheckVoteQuery($userId: ID!, $linkId: ID!) {
            viewer {
              allVotes(filter: {
                user: { id: $userId },
                link: { id: $linkId }
              }) {
                edges {
                  node {
                    id
                  }
                }
              }
            }
          }
        '''
        variables = {
            'userId': user_gid,
            'linkId': link_gid,
        }
        expected = {
            'viewer': {
                'allVotes': {
                    'edges': [
                        {
                            'node': {
                                'id': vote_gid,
                            }
                        }
                    ]
                }
            }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query, variable_values=variables)
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))


# ========== createVote mutation tests ==========

class CreateVoteTests(TestCase):
    def setUp(self):
        create_Link_orderBy_test_data()
        self.link_gid = Node.to_global_id('Link', LinkModel.objects.latest('created_at').pk)
        self.user = create_test_user()
        self.user_gid = Node.to_global_id('User', self.user.pk)
        self.query = '''
          mutation CreateVoteMutation($input: CreateVoteInput!) {
            createVote(input: $input) {
              vote {
                link {
                  id
                  votes { count }
                }
              }
              clientMutationId
            }
          }
        '''
        self.schema = graphene.Schema(query=Query, mutation=Mutation)

    @staticmethod
    def variables(link_gid, user_gid):
        return {
          'input': {
            'linkId': link_gid,
            'userId': user_gid,
            'clientMutationId': 'give_this_back_to_me',
          }
        }

    def context_with_token(self):
        class Auth(object):
            META = {'HTTP_AUTHORIZATION': 'Bearer {}'.format(self.user.token)}
        return Auth

    @staticmethod
    def context_without_token():
        class Auth(object):
            META = {}
        return Auth

    def expected(self):
        return {
          'createVote': {
            'vote': {
              'link': {
                'id': self.link_gid,
                'votes': {
                  'count': 1,
                }
              }
            },
            'clientMutationId': 'give_this_back_to_me',
          }
        }

    def test_create_vote(self):
        """test normal vote creation, and that duplicate votes are not allowed"""
        result = self.schema.execute(
            self.query,
            variable_values=self.variables(self.link_gid, self.user_gid),
            context_value=self.context_with_token()
        )
        self.assertIsNone(result.errors, msg=format_graphql_errors(result.errors))
        expected = self.expected()
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))
        # verify that a second vote can't be created
        result = self.schema.execute(self.query,
                                     variable_values=self.variables(self.link_gid, self.user_gid),
                                     context_value=self.context_with_token())
        self.assertIsNotNone(result.errors,
                             msg='createVote should have failed: duplicate votes not allowed')
        self.assertIn('vote already exists', repr(result.errors))
        expected['createVote'] = None
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_create_vote_not_logged(self):
        """ensure createVote with no logged user fails"""
        result = self.schema.execute(
            self.query,
            variable_values=self.variables(self.link_gid, self.user_gid),
            context_value=self.context_without_token()
        )
        self.assertIsNotNone(result.errors,
                             msg='createVote should have failed: no user logged-in')
        self.assertIn('Only logged-in users may vote', repr(result.errors))
        expected = { 'createVote': None }
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_create_vote_bad_userid(self):
        """ensure invalid userId causes failure"""
        result = self.schema.execute(
            self.query,
            variable_values=self.variables(self.link_gid, ' invalid base64 userId '),
            context_value=self.context_with_token()
        )
        self.assertIsNotNone(result.errors,
                             msg='createVote should have failed: invalid userId')
        self.assertIn('user id does not match logged-in user', repr(result.errors))
        expected = { 'createVote': None }
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_create_vote_user_mismatch(self):
        """ensure logged user must match supplied userId"""
        user2 = create_test_user(name='Another User', password='zyz987', email='ano@user.com')
        user2_gid = Node.to_global_id('User', user2.pk)
        result = self.schema.execute(
            self.query,
            variable_values=self.variables(self.link_gid, user2_gid),
            context_value=self.context_with_token()
        )
        self.assertIsNotNone(result.errors,
                             msg='createVote should have failed: userId and logged user mismatch')
        self.assertIn('user id does not match logged-in user', repr(result.errors))
        expected = { 'createVote': None }
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))

    def test_create_vote_bad_link(self):
        """ensure invalid linkId causes failuer"""
        last_link_pk = LinkModel.objects.order_by('id').last().pk
        invalid_link_gid = Node.to_global_id('Link', last_link_pk + 1)
        result = self.schema.execute(
            self.query,
            variable_values=self.variables(invalid_link_gid, self.user_gid),
            context_value=self.context_with_token()
        )
        self.assertIsNotNone(result.errors,
                             msg='createVote should have failed: invalid linkId')
        self.assertIn('link not found', repr(result.errors))
        expected = { 'createVote': None }
        self.assertEqual(result.data, expected, msg='\n'+repr(expected)+'\n'+repr(result.data))
