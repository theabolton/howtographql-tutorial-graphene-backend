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
