# howtographql-graphene-tutorial-fixed -- links/schema.py
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
from graphene import ObjectType, relay
from graphene_django import DjangoObjectType

from links.models import Link as LinkModel


class Link(DjangoObjectType):
    class Meta:
        model = LinkModel
        interfaces = (relay.Node, )
        # We are going to provide a custom Connection, so we need to tell graphene-django not to
        # create one. Failing to do this will result in a error like "AssertionError: Found
        # different types with the same name in the schema: LinkConnection, LinkConnection."
        use_connection = False


class LinkOrderBy(graphene.Enum):
    """This provides the schema's LinkOrderBy Enum type, for ordering LinkConnection."""
    createdAt_DESC = '-created_at'
    createdAt_ASC = 'created_at'
    description_ASC = 'description'
    description_DESC = '-description'
    id_ASC = 'id'
    id_DESC = '-id'
    #updatedAt_ASC = 'updated_at'
    #updatedAt_DESC = '-updated_at'
    url_ASC = 'url'
    url_DESC = '-url'


class LinkConnection(relay.Connection):
    """A custom Connection for queries on Link. Using this instead of DjangoConnectionField or
    DjangoFilterConnectionField solves two problems:
    - django_filters FilterSet can't use custom enums for OrderFilter choices, and
    - DjangoConnectionField in graphene-django 2.0 can no longer be given a custom Connection,
        which makes it difficult to add custom fields (such as the ubiquitous 'totalCount') on the
        connection without monkey-patching.
    """

    # total_count = graphene.Int()  -- a custom field on the connection, to be added later

    class Meta:
        node = Link

    @staticmethod
    def get_input_fields():
        return {
            'order_by': graphene.Argument(LinkOrderBy) # an input field using the custon enum
        }

    def resolve_all_links(self, info, **args):
        qs = LinkModel.objects.all()
        order_by = args.get('order_by')
        if order_by:
            qs = qs.order_by(order_by)
        return qs


class Viewer(ObjectType):
    class Meta:
        interfaces = (relay.Node, )

    all_links = relay.ConnectionField(
        LinkConnection,
        resolver=LinkConnection.resolve_all_links,
        **LinkConnection.get_input_fields()
    )


class Query(object):
    viewer = graphene.Field(Viewer)
    node = relay.Node.Field()

    def resolve_viewer(self, info):
        return not None # none of the resolvers need Viewer()
