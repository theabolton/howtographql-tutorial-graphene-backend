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

from hackernews.schema import Query
from .models import Link


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
        assert not result.errors, result.errors
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
            ]
          }
        }
        schema = graphene.Schema(query=Query)
        result = schema.execute(query)
        assert not result.errors, result.errors
        # Check that the fields we need are there, but don't fail on extra fields.
        NEEDED_FIELDS = ('id', 'allLinks')
        result.data['__type']['fields'] = list(filter(
            lambda f: f['name'] in NEEDED_FIELDS,
            result.data['__type']['fields']
        ))
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)


def create_Links_orderBy_test_data():
    """Create test data for LinkConnection orderBy tests. Create three links,
    with description, url, and created_at each having a different sort order."""
    import datetime
    import pytz
    def dt(epoch):
        return datetime.datetime.fromtimestamp(epoch).replace(tzinfo=pytz.utc)
    link = Link(description='Description C', url='http://a.com')
    link.save()  # give 'auto_now_add' a chance to do its thing
    link.created_at = dt(1000000000) # new time stamp, least recent
    link.save()
    link = Link(description='Description B', url='http://b.com')
    link.save()
    link.created_at = dt(1000000400) # most recent
    link.save()
    link = Link(description='Description A', url='http://c.com')
    link.save()
    link.created_at = dt(1000000200)
    link.save()


class LinkTests(TestCase):
    def test_all_links(self):
        link = Link(description='Description', url='http://')
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
        assert not result.errors, result.errors
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)

    def test_all_links_ordered_by(self):
        create_Links_orderBy_test_data()
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
        assert not result.errors, result.errors
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
        assert not result.errors, result.errors
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)

    def test_all_links_pagination(self):
        """Make sure that pagination still works on the custom LinkConnection."""
        create_Links_orderBy_test_data()
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
        assert not result.errors, result.errors
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
        assert not result.errors, result.errors
        assert result.data == expected, '\n'+repr(expected)+'\n'+repr(result.data)
