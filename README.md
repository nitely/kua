# kua

[![Build Status](https://img.shields.io/travis/nitely/kua.svg?style=flat-square)](https://travis-ci.org/nitely/kua)
[![Coverage Status](https://img.shields.io/coveralls/nitely/kua.svg?style=flat-square)](https://coveralls.io/r/nitely/kua)
[![pypi](https://img.shields.io/pypi/v/kua.svg?style=flat-square)](https://pypi.python.org/pypi/kua)
[![licence](https://img.shields.io/pypi/l/kua.svg?style=flat-square)](https://raw.githubusercontent.com/nitely/kua/master/LICENSE)

Lightning fast URL routing in Python.

kua is a [Trie](https://en.wikipedia.org/wiki/Trie)-like based router.
It scales better than regex based routers and due to this it's usually faster.

It's pretty bare bones and it's meant to be used in more feature-rich routers.


## Compatibility

* Python 3.5


## Install

```
$ pip install kua
```


## Usage

```python
import kua

routes = kua.Routes()
routes.add('api/:foo', {'GET': my_get_controller})
route = routes.match('api/hello-world')
route.params
# {'foo': 'hello-world'}
route.anything
# {'GET': my_get_controller}
```


# Docs

[Read The Docs](http://kua.readthedocs.io)


## Tests

```
$ make test
```


# Backtracking

Backtracking means kua will have to try more than one path to match the URL.

This *may* hurt performance, depending how much backtracking is involved,
usually you should not worry about it, though.

This reduces to not placing two variables next to each other and not placing
a variable where there is a static one in a similar pattern.

Here are some examples of good and bad schemas:

```python
# bad
routes.add(':var', ...)  # clashes with pretty much every pattern

# still bad
routes.add(':var1/:var2', ...)

# bad
routes.add(':var1/foo', ...)

# still bad
routes.add(':var1/:var2/foo', ...)

# bad
routes.add('api/:var1', ...)
routes.add('api/foo', ...)

# still bad
routes.add('api/:var1/:var2', ...)
routes.add('api/foo', ...)

# still bad
routes.add('api/:var1/foo', ...)
routes.add('api/foo', ...)

# good
routes.add('api', ...)
routes.add('api/:var', ...)
routes.add('api/:var/foo', ...)
routes.add('api/:var/bar', ...)
routes.add('api/:var/foo/:var2', ...)
routes.add('api/:var/bar/:var2', ...)

# good
routes.add('topics', ...)
routes.add('topics/:var', ...)
routes.add('authors', ...)
routes.add('authors/:var', ...)

# good
routes.add('shelf', ...)
routes.add('shelf/books', ...)
routes.add('shelf/books/:var', ...)

# good
routes.add('books/all', ...)
routes.add('books/removed', ...)
routes.add('books/pending', ...)
```


## License

MIT
