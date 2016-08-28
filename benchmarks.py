from kua import routes


if __name__ == '__main__':
    import timeit
    import functools

    def controller(): pass

    routes_ = routes.Routes()
    routes_.add(':foo/:bar/:baz/:last', controller)
    routes_.add('api/:bar/:baz/:last', controller)
    routes_.add('api/id', controller)

    print(timeit.timeit(functools.partial(routes_.match, 'api/id/baz/last'), number=150000))
