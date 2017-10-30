import graphene

import links.schema


class Query(links.schema.Query, graphene.ObjectType):
    pass


class Mutation(links.schema.Mutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
