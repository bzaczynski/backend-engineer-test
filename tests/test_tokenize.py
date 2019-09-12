from typing import Generator

from articles.import_data import tokenize


def test_should_return_generator():
    assert isinstance(tokenize('some text'), Generator)


def test_should_remove_whitespace_and_non_alpha():
    actual = tokenize('  Lorem,   ipsum\tdolor!')
    assert list(actual) == ['lorem', 'ipsum', 'dolor']
