# coding:utf-8

import functools


def login_required(func):

    @functools.wraps(func)
    def wrapper(*arg, **kwargs):
        pass

    return wrapper


@login_required
def cat():
    """cat python"""
    pass

# cat ->  wrapper

print(cat.__name__)  # wrapper.__name__
print(cat.__doc__)   # wrapper.__doc__