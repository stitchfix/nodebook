from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
import pandas as pd
import pytest
from nodebook.pickledict import PickleDict


@pytest.fixture(params=[None, 'tmpdir'], ids=['mode_memory', 'mode_disk'])
def mydict(request, tmpdir):
    if request.param == 'tmpdir':
        persist_path = tmpdir.strpath
        print(persist_path)
    else:
        persist_path = None
    return PickleDict(persist_path=persist_path)


class TestPickleDict(object):
    def test_int(self, mydict):
        mydict['test_int'] = 42
        assert mydict['test_int'] == 42

    def test_string(self, mydict):
        mydict['test_string'] = 'foo'
        assert mydict['test_string'] == 'foo'

        d = {'foo':'bar'}
        mydict['test_string_dict'] = d
        assert mydict['test_string_dict'] == d

    def test_bytes(self, mydict):
        mydict['test_bytes'] = b'foo'
        assert mydict['test_bytes'] == b'foo'

        d = {b'foo':b'bar'}
        mydict['test_bytes_dict'] = d
        assert mydict['test_bytes_dict'] == d

    def test_list(self, mydict):
        l = [1,2,3]
        mydict['test_list'] = l
        assert mydict['test_list'] == l

    def test_tuple(self, mydict):
        t = (1,2,3)
        mydict['test_tuple'] = t
        assert mydict['test_tuple'] == t

    def test_set(self, mydict):
        s = {1,2,3}
        mydict['test_set'] = s
        assert mydict['test_set'] == s

    def test_df(self, mydict):
        df = pd.DataFrame({'a': [0, 1, 2], 'b': ['foo', 'bar', 'baz']})
        mydict['test_df'] = df
        assert mydict['test_df'].equals(df)
        
    def test_func(self, mydict):
        def add(a, b):
            return a + b
        mydict['test_func'] = add
        assert mydict['test_func'](3,5) == 8

    def test_closure(self, mydict):
        df = pd.DataFrame({'a': [0, 1, 2], 'b': ['foo', 'bar', 'baz']})
        def foo():
            return df
        def bar():
            return foo()
        mydict['test_closure'] = bar
        assert mydict['test_closure']().equals(df)

    def test_immutability(self, mydict):
        l = [1, 2, 3]
        mydict['test_mut'] = l
        assert mydict['test_mut'] == l
        l.append(42)
        assert not mydict['test_mut'] == l
