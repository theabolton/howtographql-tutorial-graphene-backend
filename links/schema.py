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

import django_filters

import graphene
from graphene import ObjectType, relay
from graphene.relay import Node
from graphene_django import DjangoObjectType

from links.models import LinkModel, VoteModel
from users.schema import get_user_from_auth_token, User


# ========== Vote ==========

# There are two common GraphQL schema patterns that are difficult to implement with graphene-django
# 2.0 without distasteful monkey-patching. These are:
#
# - DjangoConnectionField can no longer be given a custom Connection, which makes it difficult to
#   add custom fields (such as the ubiquitous 'count' or 'totalCount') on the connection, and
#
# - django_filters FilterSet can't use custom Enums for OrderingFilter choices.
#
# The VoteConnection here demonstrates how to use a custom Connection, with a 'count' field and
# a non-Enum-using FilterSet, with no monkey patching.
#
# LinkConnection below demonstrates a way to use custom Enums in a custom Connection.

class Vote(DjangoObjectType):
    class Meta:
        model = VoteModel
        interfaces = (relay.Node, )
        # We are going to provide a custom Connection, so we need to tell graphene-django not to
        # create one. Failing to do this will result in a error like "AssertionError: Found
        # different types with the same name in the schema: VoteConnection, VoteConnection."
        use_connection = False


class IdInput(graphene.InputObjectType):
    id = graphene.ID(required=True)


class VoteFilter(graphene.InputObjectType):
    """The input object for filtered allVotes queries. The VoteFilter input type provided by the
    Graphcool server used in the front-end tutorial is quite a bit more complex than this, but this
    is all the tutorial itself needs.
    """
    link = graphene.InputField(IdInput)
    user = graphene.InputField(IdInput)


class VotesFilterSet(django_filters.FilterSet):
    """A basic FilterSet for filtering allVotes queries."""
    class Meta:
        model = VoteModel
        fields = ['link', 'user']


class VoteConnection(relay.Connection):
    """A custom Connection for queries on Vote, complete with custom field 'count'."""
    class Meta:
        node = Vote

    count = graphene.Int()

    # 'allVotes' is actually a field on Viewer, and 'votes' is a field on Link, but rather than put
    # a bunch of Vote-related logic in Viewer and Link, I prefer to keep it here as static methods
    # on VoteConnection.
    @staticmethod
    def get_all_votes_input_fields():
        """Return the input fields needed by allVotes."""
        return {
            'filter': graphene.Argument(VoteFilter),
        }

    @staticmethod
    def resolve_all_votes(_, info, **args):
        """Resolve a field returning a (possibly filtered view of) all Votes."""
        qs = VoteModel.objects.all()
        filter = args.get('filter', None)
        if filter:
            # We don't get the free input marshalling that DjangoFilterConnectionField provides, so
            # we have to do that ourselves.
            for key, field in filter.items():
                # collapse e.g.:
                #     { 'link': { 'id': '<global_id>' } }  # what graphene provides
                # to:
                #     { 'link': '<primary_key>' }  # what our FilterSet expects
                if key in ('link', 'user'):
                    id = field.get('id', None)
                    if id:
                        _, filter[key] = Node.from_global_id(id)
            qs = VotesFilterSet(data=filter, queryset=qs).qs
        return qs

    def resolve_count(self, info, **args):
        """Return the count of votes in the LinkConnection query."""
        # self.iterable is the QuerySet of VoteModels
        return self.iterable.count()

    @staticmethod
    def resolve_votes(parent, info, **args):
        """Resolve the 'votes' field on Link by returning all votes made by this user."""
        # parent is a LinkModel
        qs = VoteModel.objects.filter(link_id=parent.pk)
        return qs


class CreateVote(relay.ClientIDMutation):
    # mutation CreateVoteMutation($input: CreateVoteInput!) {
    #   createVote(input: $input) {
    #     vote {
    #       id
    #       link {
    #         id
    #         votes { count }
    #       }
    #       user { id }
    #     }
    #   }
    # }
    # example variables:
    #   input {
    #     userId: 'VXNlcjox',
    #     linkId: 'TGluazoy',
    #     clientMutationId: ''
    #   }

    vote = graphene.Field(Vote, required=True)

    class Input:
        user_id = graphene.ID()
        link_id = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, link_id, user_id, client_mutation_id=None):
        user = get_user_from_auth_token(info.context) or None
        if not user:
            raise Exception('Only logged-in users may vote!')
        if user_id:
            user_from_id = Node.get_node_from_global_id(info, user_id)
            if (not user_from_id) or (user_from_id.pk != user.pk):
                raise Exception('Supplied user id does not match logged-in user!')
        link = Node.get_node_from_global_id(info, link_id)
        if not link:
            raise Exception('Requested link not found!')
        if VoteModel.objects.filter(user_id=user.pk, link_id=link.pk).count() > 0:
            raise Exception('A vote already exists for this user and link!')

        vote = VoteModel(user_id=user.pk, link_id=link.pk)
        vote.save()

        return CreateVote(vote=vote)


# ========== Link ==========

# The GraphQL schema used by the front-end tutorial uses GraphQL Enums for specifying the sort order
# used by its connections, for example:
#
#     enum LinkOrderBy {
#       createdAt_ASC
#       createdAt_DESC
#       description_ASC
#       description_DESC
#       id_ASC
#       id_DESC
#       updatedAt_ASC
#       updatedAt_DESC
#       url_ASC
#       url_DESC
#     }
#
# graphene_django has some provision for generating Enums from choice-containing fields in a
# DjangoObjectType, but the Enum type name and value names are automatically generated with no way
# to control them. Furthermore, for the tutorial we need the Enum types for ordering the
# LinkConnection, and DjangoFilterConnectionType makes no provision for custom enums in FilterSets.
# So, we're back to using a custom Connection.

class Link(DjangoObjectType):
    class Meta:
        model = LinkModel
        interfaces = (Node, )
        use_connection = False  # a custom Connection will be provided

    votes = relay.ConnectionField(
        VoteConnection,
        resolver=VoteConnection.resolve_votes,
        #**VoteConnection.get_votes_input_fields() -- no input fields (yet)
    )

class LinkOrderBy(graphene.Enum):
    """This provides the schema's LinkOrderBy Enum type, for ordering LinkConnection."""
    # The class name ('LinkOrderBy') is what the GraphQL schema Enum type name should be, the
    # left-hand side below is what the Enum values should be, and the right-hand side is what our
    # resolver will receive.
    createdAt_DESC = '-created_at'
    createdAt_ASC = 'created_at'
    description_ASC = 'description'
    description_DESC = '-description'
    id_ASC = 'id'
    id_DESC = '-id'
    #updatedAt_ASC = 'updated_at'   -- these are present in the Graphcool schema, but not needed by
    #updatedAt_DESC = '-updated_at'    the tutorial, nor implemented in LinkModel
    url_ASC = 'url'
    url_DESC = '-url'


class LinkConnection(relay.Connection):
    """A custom Connection for queries on Link."""
    class Meta:
        node = Link

    @staticmethod
    def get_all_links_input_fields():
        return {
            # this creates an input field using the LinkOrderBy custom enum
            'order_by': graphene.Argument(LinkOrderBy)
        }

    def resolve_all_links(self, info, **args):
        qs = LinkModel.objects.all()
        order_by = args.get('order_by', None)
        if order_by:
            # Graphene has already translated the over-the-wire enum value (e.g. 'createdAt_DESC')
            # to our internal value ('-created_at') needed by Django.
            qs = qs.order_by(order_by)
        return qs


class CreateLink(relay.ClientIDMutation):
    # mutation CreateLinkMutation($input: CreateLinkInput!) {
    #   createLink(input: $input) {
    #     link {
    #       id
    #       createdAt
    #       url
    #       description
    #     }
    #   }
    # }
    # example variables:
    #   input {
    #       description: "New Link",
    #       url: "http://example.com",
    #       postedById: 1,
    #       clientMutationId: "",
    #   }

    link = graphene.Field(Link, required=True)

    class Input:
        description = graphene.String(required=True)
        url = graphene.String(required=True)
        posted_by_id = graphene.ID()

    @classmethod
    def mutate_and_get_payload(cls, root, info, url, description, posted_by_id=None,
                               client_mutation_id=None):
        # In order to have this work with early stages of the front-end tutorial, this will allow
        # links to be created without a user auth token or postedById. If a postedById is present,
        # then the auth token must be as well. If both are present, then they must agree.
        user = get_user_from_auth_token(info.context) or None
        if user or posted_by_id:
            if not user:
                raise Exception('Only logged-in users may create links!')
            if posted_by_id:
                try:
                    posted_by_user = Node.get_node_from_global_id(info, posted_by_id)
                    assert posted_by_user.pk == user.pk
                except:
                    raise Exception('postedById does not match user ID!')
        link = LinkModel(
            url=url,
            description=description,
            posted_by=user,
        )
        link.save()

        return CreateLink(link=link)


# ========== schema structure ==========

# A common question I've seen regarding graphene, and GraphQL back-ends in general, is "what creates
# this 'viewer' field my front-end is expecting?" Many Relay applications have GraphQL schemas that
# include a 'viewer' field, but 'viewer' is not part of the GraphQL or Relay specifications.
# Instead, it is just a common and useful pattern for introducing user authentication and/or
# grouping top-level queries. Here is a simple viewer implementation, which includes the requisite
# Relay Node and wraps our top-level queries. Note that there's no Django involved at this level,
# just graphene routing queries to the appropriate resolvers.

class Viewer(ObjectType):
    class Meta:
        interfaces = (Node, )

    all_links = relay.ConnectionField(
        LinkConnection,
        resolver=LinkConnection.resolve_all_links,
        **LinkConnection.get_all_links_input_fields()
    )

    all_votes = relay.ConnectionField(
        VoteConnection,
        resolver=VoteConnection.resolve_all_votes,
        **VoteConnection.get_all_votes_input_fields()
    )


class Query(object):
    viewer = graphene.Field(Viewer)
    node = Node.Field()

    def resolve_viewer(self, info):
        return not None # none of Viewer's resolvers need Viewer()


class Mutation(object):
    create_link = CreateLink.Field()
    create_vote = CreateVote.Field()
