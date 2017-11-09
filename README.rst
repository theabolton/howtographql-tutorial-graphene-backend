++++++++++++++++++++++++++++++++++++++
howtographql-tutorial-graphene-backend
++++++++++++++++++++++++++++++++++++++

|license| |build|

.. |license| image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://en.wikipedia.org/wiki/MIT_License
   :alt: MIT Licensed

.. |build| image:: https://travis-ci.org/smbolton/howtographql-tutorial-graphene-backend.svg?branch=master
   :target: https://travis-ci.org/smbolton/howtographql-tutorial-graphene-backend
   :alt: Documentation Status

HowtoGraphQL.com_ hosts a series of tutorials whose aim is teaching GraphQL_ and a number of
common software packages that use GraphQL, through the construction of a simple imitation of
`Hacker News`_. Unfortunately, the `Python/Django/Graphene backend server tutorial`_ is incomplete
in that it does not work with the `React+Relay frontend tutorial`_.

.. _HowtoGraphQL.com: https://www.howtographql.com/
.. _GraphQL: http://graphql.org/
.. _Hacker News: https://news.ycombinator.com/
.. _Python/Django/Graphene backend server tutorial: https://www.howtographql.com/graphql-python/0-introduction/
.. _React+Relay frontend tutorial: https://www.howtographql.com/react-relay/0-introduction/

This project implements a backend server that it actually works with the frontend tutorial.

Even if you're not looking for a working Graphene backend for the frontend tutorial, you may be
interested in this project if:

* You've wondered what the ``viewer`` field found in many GraphQL schemas is, and how to implement
  it in Graphene. See `The Viewer Field`_, below.

* You want to implement a custom field (like ``totalCount``) on a Connection, but
  DjangoConnectionField won't let you. See `Custom Connections`_.

* You want to use custom Enum types in you schema, but DjangoObjectType won't let you choose their
  names, and DjangoFilterConnectionField won't let you use them at all. See `Custom Enums`_.

* You're looking for examples of how to use Graphene 2.0. (The backend tutorial is written for
  pre-2.0 Graphene.)

.. warning::

   The GraphQL ecosystem is rapidly evolving, and at this time (November 2017), the newly-released
   Graphene 2.0 is a bit of a mess. While Graphene holds lots of promise, be aware that it currently
   has no API documentation (just some "how to" docs), almost no comments in the code, and much of
   the help you'll find online (e.g. on stackoverflow_) is written for pre-2.0 Graphene. If you're
   new to GraphQL, Python, or Graphene, working with it can be a challenge. But then, that's why I
   decided to publish this, in the hope that it will be helpful!

.. _stackoverflow: https://stackoverflow.com/questions/tagged/graphene-python

Note that because things are in such a flux, especially subscriptions, I have not yet implemented
part 7 (video chapter 8) of the tutorial, which implements a subscription on the front end. Once
the graphene-django subscription support stabilizes, I'll add that.

Installation
============

.. code:: shell

   $ git clone https://github.com/smbolton/howtographql-tutorial-graphene-backend.git
   $ cd howtographql-tutorial-graphene-backend
   $ virtualenv --python=python3 venv
   $ source venv/bin/activate
   $ pip install -r requirements.txt
   $ ./manage.py makemigrations
   $ ./manage.py migrate
   $ ./manage.py test  # all tests should pass
   $ ./manage.py runserver

The server includes the GraphiQL_ schema-browser IDE, so once you have the server running, point
your browser at:

http://localhost:8000/graphql/

and you will be able to browse the schema and submit test queries.

.. _GraphiQL: https://github.com/graphql/graphiql

Required Changes to the Frontend Tutorial
=========================================
The frontend tutorial assumes the use of Graphcool's backend prototyping service for the backend
server. We want to replace that with this Graphene-based server, so there are two changes that need
to be made to the tutorial frontend code. Both happen in the `Getting Started`_ section (Chapter 2
in the videos).

.. _Getting Started: https://www.howtographql.com/react-relay/1-getting-started/

1. Once you have run ``create-react-app``, add the following to ``package.json``:

   .. code-block:: json

      "proxy": "http://localhost:8000",

   This tells the webpack development server to proxy any unexpected (i.e. non-Relay) requests to
   our Graphene server. Using proxying like this keeps things simpler by allowing us to avoid
   setting up Cross-Origin Resource Sharing (CORS).

2. When you get to the part were it has you find the Graphcool server Relay API endpoint:

      Open up a terminal ... and execute the following command:

      .. code:: shell

         graphcool endpoints

      ...

      Copy the endpoint from the terminal output and paste it into ``src/Environment.js`` replacing
      the current placeholder ``__RELAY_API_ENDPOINT__``.

   skip that, and use ``http://localhost:3000/graphql/`` for the endpoint, so the relevant line in
   ``src/Environment.js`` will look like this:

   .. code:: shell

      return fetch('http://localhost:3000/graphql/', {

That's all the changes to the frontend tutorial that you need to make! (But remember that this
back end does not yet implement the subscription feature covered in the tutorial part 7 (video
chapter 8). You can work through part 7 without anything breaking, the live update just won't work,
or you can skip over it and go directly to part 8.)

The Viewer Field
================
A common question I've seen regarding Graphene, and GraphQL back-ends in general, is "what creates
this 'viewer' field my front-end is expecting?" Many Relay applications have GraphQL schemas that
include a 'viewer' field, but 'viewer' is not part of the GraphQL or Relay specifications.
Instead, it is just a common and useful pattern for introducing user authentication and/or
grouping top-level queries.

Here is a simple viewer implementation, which creates a ``viewer`` field directly under the root
query, and contains an ``allLinks`` field by which all link objects can be queried. It also
includes the requisite Relay Node. Note that there's no Django involved at this level, just Graphene
routing queries to the appropriate resolvers.

.. code:: python

   class Viewer(graphene.ObjectType):
       class Meta:
           interfaces = (graphene.relay.Node, )

       # add an 'allLinks' field to 'viewer'
       all_links = graphene_django.DjangoConnectionField(Link)

   class Query(object):
       viewer = graphene.Field(Viewer)
       node = graphene.relay.Node.Field()

       @staticmethod
       def resolve_viewer(self, info):
           return Viewer()

You can find the full implementation of this Viewer in `links/schema.py`_

.. _`links/schema.py`: https://github.com/smbolton/howtographql-tutorial-graphene-backend/blob/links/schema.py#L316-338

Custom Connections
==================
In the above example, I used ``DjangoConnectionField`` as an easy way to add an ``allLinks``
Connection field to my ``Link`` Node type. This works really well, automatically building the
Connection class with resolvers for our model and all the node and pagination fields that Relay
needs. “Well”, that is, until we need to customize that connection. `Sometime
<custom_connection_loss>`_ in the development of 2.0, Graphene lost the ability to use custom
Connections without ugly monkey patching.

.. _custom_connection_loss: https://github.com/graphql-python/graphene-django/commit/4cc46736bf7297d3f927115daedd1c332c7a38ef#diff-02f0e8baa98448ee267f8be14990558c

Why would one need to customize a Connection? One example would be to implement the ``count`` or
``totalCount`` field that is so common in Relay applications:

.. code-block:: graphql

   query {
     viewer {
       allVotes {
         count # give me the count of all Votes
       }
     }
   }

Here is a simple example of using a custom connection to implement ``count``:

.. code-block:: python

   class Vote(graphene_django.DjangoObjectType):
       class Meta:
           model = models.VoteModel
           interfaces = (graphene.relay.Node, )
           # We are going to provide a custom Connection, so we need to tell
           # graphene-django not to create one. Failing to do this will result
           # in a error like "AssertionError: Found different types with the
           # same name in the schema: VoteConnection, VoteConnection."
           use_connection = False

   class VoteConnection(graphene.relay.Connection):
       """A custom Connection for queries on Vote, complete with custom field 'count'."""
       class Meta:
           node = Vote

       count = graphene.Int()

       @staticmethod
       def resolve_count(self, info, **args):
           # self.iterable is the QuerySet returned by resolve_all_votes()
           return self.iterable.count()

   class Viewer(graphene.ObjectType):
       class Meta:
           interfaces = (graphene.relay.Node, )

       all_votes = relay.ConnectionField(VoteConnection)

       @staticmethod
       def resolve_all_votes(_, info, **args):
           qs = models.VoteModel.objects.all()
           return qs

Notice how the ``allVotes`` field is part of ``Viewer``, and so ``resolve_all_votes()`` pulls vote-
related logic into ``Viewer``, instead of it being up with ``Vote`` and ``VoteConnection`` instead?
Since Graphene resolvers are static methods anyway, I move them into the class they return (here
``VoteConnection``), instead of the class they are called from (``Viewer``), which feels a little
odd at first, but allows me to keep everything much more organized and modular:

.. code-block:: python

   class VoteConnection(graphene.relay.Connection):
       ...
       @staticmethod
       def resolve_all_votes(_, info, **args):
           """Resolver for the ``Viewer`` ``allLinks`` field."""
           qs = models.VoteModel.objects.all()
           return qs

   class Viewer(graphene.ObjectType):
       ...
       all_votes = relay.ConnectionField(
           VoteConnection
           resolver=VoteConnection.resolve_all_votes
       )

       # no Vote-related code here!

For a more complex example, including the use of a django-filter_ ``FilterSet`` to filter the votes
returned by ``allVotes``, see `links/schema.py <vote_connection>`_.

.. _django-filter: https://django-filter.readthedocs.io/en/master/
.. _vote_connection: https://github.com/smbolton/howtographql-tutorial-graphene-backend/blob/links/schema.py#L35-129

Custom Enums
============
One more challenge presented by Graphene when trying to match the How To GraphQL tutorial schema, is
the schema's use of custom GraphQL Enums to specify the sort order used by its connections, for
example:

.. code-block:: graphql

   enum LinkOrderBy {
     createdAt_ASC
     createdAt_DESC
     ...
   }

   query {
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

graphene_django has some provision for generating Enums from choice-containing fields in a
``DjangoObjectType``, but the Enum type name and value names are automatically generated with no way
to control them. Furthermore, for the tutorial we need the Enum types for ordering the
``LinkConnection``, and ``DjangoFilterConnectionType`` makes no provision at all for custom enums in
``FilterSet`` s. So, we're back to using a custom Connection.

Here is a simple example of using custom Enums on a connection:

.. code-block:: python

   class LinkOrderBy(graphene.Enum):
       """This provides the schema's LinkOrderBy Enum type, for ordering LinkConnection."""
       # The class name ('LinkOrderBy') is what the GraphQL schema Enum type
       # name should be, the left-hand side below is what the Enum values should
       # be, and the right-hand side is what our resolver will receive.
       createdAt_ASC = 'created_at'
       createdAt_DESC = '-created_at'

   class LinkConnection(graphene.relay.Connection):
       """A custom Connection for queries on Link."""
       class Meta:
           node = Link

       @staticmethod
       def get_all_links_input_fields():
           return {
               # this creates an input field using the LinkOrderBy custom enum
               'order_by': graphene.Argument(LinkOrderBy)
           }

       @staticmethod
       def resolve_all_links(self, info, **args):
           qs = models.LinkModel.objects.all()
           order_by = args.get('order_by', None)
           if order_by:
               # Graphene has already translated the over-the-wire enum value
               # (e.g. 'createdAt_DESC') to our internal value ('-created_at')
               # needed by Django.
               qs = qs.order_by(order_by)
           return qs

   class Viewer(ObjectType):
       class Meta:
           interfaces = (graphene.relay.Node, )

       all_links = graphene.relay.ConnectionField(
           LinkConnection,
           resolver=LinkConnection.resolve_all_links,
           **LinkConnection.get_all_links_input_fields()
       )

The full version of this can be found in `links/schema.py <custom_enums>`_.

.. _custom_enums: https://github.com/smbolton/howtographql-tutorial-graphene-backend/blob/links/schema.py#L179-251

License
=======
Copyright © 2017 Sean Bolton.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
