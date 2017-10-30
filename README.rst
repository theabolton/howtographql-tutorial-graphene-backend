++++++++++++++++++++++++++++++++++++
howtographql-graphene-tutorial-fixed
++++++++++++++++++++++++++++++++++++

|license|

.. |license| image:: https://img.shields.io/badge/License-MIT-yellow.svg
   :target: https://en.wikipedia.org/wiki/MIT_License
   :alt: MIT Licensed

HowtoGraphQL.com_ hosts a series of tutorials whose aim is teaching GraphQL_ and a number of
common software packages that use GraphQL, through the construction of a simple imitation of
`Hacker News`_. Unfortunately, the `Python/Django/graphene backend server tutorial`_ is incomplete
in that it does not work with the `React+Relay frontend tutorial`_.

.. _HowtoGraphQL.com: https://www.howtographql.com/
.. _GraphQL: http://graphql.org/
.. _Hacker News: https://news.ycombinator.com/
.. _Python/Django/graphene backend server tutorial: https://www.howtographql.com/graphql-python/0-introduction/
.. _React+Relay frontend tutorial: https://www.howtographql.com/react-relay/0-introduction/

This project fixes and extends the backend server so that it actually works with the frontend
tutorial.

Even if you're not trying to get the two tutorials to work with each other, you may be interested
in this project if:

* You've wondered what the ``viewer`` field found in many GraphQL schemas is, and how to implement
  it in graphene.

.. warning::

   Note that at this time (November 2017), the newly-released graphene 2.0 is a mess. Don't use it.
   It won't do what you need (e.g. custom ``Connection`` s on ``DjangoConnectionObject`` s),
   there's no API documentation, almost no comments in the code, and the backend tutorial is still
   written for pre-2.0 graphene.

Installation
============

.. code:: shell

   $ git clone https://github.com/smbolton/howtographql-graphene-tutorial-fixed.git
   $ cd howtographql-graphene-tutorial-fixed
   $ virtualenv --python=python3.6 venv
   $ source venv/bin/activate
   $ pip install -r requirements.txt
   $ ./manage.py makemigrations
   $ ./manage.py migrate
   $ ./manage.py test
   $ ./manage.py runserver

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
