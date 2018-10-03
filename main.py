from typing import Any, Callable, List, NoReturn, Optional, Union

import flask
import functools


Components = Optional[List['Component']]
Parent = Union['Component', 'Handler']
RouteLike = Union['Route', 'Include']
Routes = Optional[List[RouteLike]]


class Component:
    """Componenet type.

    The "Decorator Class" in the decorator design pattern.  Decorator
    classes are called "components" to avoid confusion with python
    @decorators.

    If a component does not implement any of the methods of the
    concrete class it will act as a pass-through.
    """

    def __init__(self, parent: Parent) -> None:
        self.parent = parent

    def __getattr__(self, name: str) -> Any:
        return getattr(self.parent, name)


class Handler:
    """Handler type.

    The "Concreate Class" in the decorator design pattern.  Handlers by
    default do nothing.  You must add your own functionality by
    subclassing this type.
    """

    pass


def dispatch_request(fn: Callable, decorators: List[Parent], **uri_args: str):
    # Initialize the concrete class.  The concrete class will always
    # exist at the end of the list.
    handler = decorators.pop()
    handler = handler()

    # Initialize each of the remaining decorators being sure to
    # populate their __init__ with the previously initialized class.
    while decorators:
        decorator = decorators.pop()
        handler = decorator(handler)

    # Return the result of the decorated class's __call__ method.
    return fn(handler, **uri_args)


class Route:

    def __init__(
            self,
            path: str,
            controller: Callable,
            handler: Handler,
            method: str = 'GET',
            name: str = '',
            components: Components = None) -> None:
        self.path = path
        self.controller = controller
        self.handler = handler
        self.method = method
        self.name = name
        self.components = components or []


class Include:

    def __init__(
            self,
            prefix: str,
            routes: Routes,
            components: Components = None,
            namespace: str = '') -> None:
        self.prefix = prefix
        self.routes = routes
        self.components = components or []
        self.namespace = namespace


class Router:

    def __init__(self, app: flask.Flask) -> None:
        self.app = app

    def add_routes(
            self, routes: Routes, components: Components = None,
            prefix: str = '', namespace: str = '') -> None:
        """Add URL rules to the app for each route."""
        components = components or []
        for route in routes:
            self.add_route(route, components, prefix, namespace)

    def add_route(
            self, route: RouteLike, components: List[Component],
            prefix: str = '', namespace: str = '') -> None:
        """Add a URL rule to the app."""
        if isinstance(route, Include):
            # Concatenate the namespaces.
            namespace = '{}{}'.format(namespace, route.namespace)

            # Concatenate the prefixes.
            prefix = '{}{}'.format(prefix, route.prefix)

            # Concatenate the components lists being careful not to
            # mutate the list.
            components = components + route.components

            # Call the "add_routes" method until we reach a "Route"
            # type.
            self.add_routes(route.routes, components, prefix, namespace)

        elif isinstance(route, Route):
            # Construct the route name.
            name = '{}{}'.format(namespace, route.name) or None

            # Construct the URI path.
            path = '{}{}'.format(prefix, route.path)

            # Concatenate components with the concrete class in last
            # place.
            components = components + route.components + [route.handler]

            # Construct a function with the components pre-specified.
            handler = dispatch_request
            handler = functools.partial(handler, fn=route.controller, decorators=components)

            # Add the URL rule.
            app.add_url_rule(path, name, handler, methods=[route.method])


# Define a controller which will execute business logic.


def controller(handler, **uri_args):
    print(handler.test())
    return 'hello, world!'


# Define a handler which will define business logic.


class JSONAPIHandler(Handler):

    def test(self, **uri_args):
        return {'hello': 'world'}


# Define some decorators to add behaviors.


class A(Component):
    
    def test(self, **uri_args):
        result = self.parent.test(**uri_args)
        result['A'] = True
        return result


class B(Component):
    
    def test(self, **uri_args):
        result = self.parent.test(**uri_args)
        result['B'] = True
        return result


# Define a helper class to always pass your handler.
JSONAPIRoute = functools.partial(Route, handler=JSONAPIHandler)


# Define some routes.
routes = []
routes.append(
    Include(
        '/users', [
            JSONAPIRoute('/<id>', controller, components=[B], name='test')
        ],
        components=[A]
    )
)


# Test data.
app = flask.Flask(__name__)

api = Router(app)
api.add_routes(routes)

with app.app_context():
    client = app.test_client()
    get = client.get('/users/1')
    print(get.data.decode('utf-8'))
