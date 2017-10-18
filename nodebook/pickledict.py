from __future__ import absolute_import
import io
import os
from functools import partial
import hashlib
import pandas as pd
import msgpack
import inspect
import six

# using dill instead of pickle for more complete serialization
import dill

# Use cStringIO if available.
try:
    from cStringIO import StringIO
except ImportError:
    try:
        from StringIO import StringIO
    except ImportError:
        # Python3. We are using StringIO as a target for pickle, so we
        # actually want BytesIO.
        from io import BytesIO as StringIO

try:
    from UserDict import DictMixin
except ImportError:
    # see https://github.com/flask-restful/flask-restful/pull/231/files
    from collections import MutableMapping as DictMixin

PANDAS_CODE = 1
DILL_CODE = 2


def msgpack_serialize(obj):
    if type(obj) is pd.DataFrame or type(obj) is pd.Series:
        try:
            return msgpack.ExtType(PANDAS_CODE, obj.to_msgpack())
        except:
            # pandas msgpack support is experimental and sometimes fails
            return msgpack.ExtType(DILL_CODE, dill.dumps(obj, recurse=True))
    else:
        if inspect.isclass(obj):
            # dynamically defined classes default to __builtin__ but are only serializable in __main__
            if obj.__module__ == '__builtin__':
                obj.__module__ = '__main__'
        return msgpack.ExtType(DILL_CODE, dill.dumps(obj, recurse=True))


def msgpack_deserialize(code, data):
    if code == PANDAS_CODE:
        return pd.read_msgpack(data)
    elif code == DILL_CODE:
        return dill.loads(data)
    else:
        return msgpack.ExtType(code, data)


class PickleDict(DictMixin):
    """
    Dictionary with immutable elements using pickle(dill), optionally supporting persisting to disk
    """

    def __init__(self, persist_path=None):
        """
        persist_path: if provided, perform serialization to/from disk to this path
        """
        self.persist_path = persist_path
        self.encodings = {}
        self.dump = partial(msgpack.dump, default=msgpack_serialize)
        self.load = partial(msgpack.load, ext_hook=msgpack_deserialize)
        self.dict = {}

    def keys(self):
        return list(self.dict.keys())

    def __len__(self):
        return len(self.dict)

    def has_key(self, key):
        return key in self.dict

    def __contains__(self, key):
        return key in self.dict

    def get(self, key, default=None):
        if key in self.dict:
            return self[key]
        return default

    def __iter__(self):
        for key in self.dict:
            yield key

    def __getitem__(self, key):
        if self.persist_path is not None:
            path = self.dict[key]
            with open(path, 'rb') as f:
                value = self.load(f, encoding=self.encodings[key])
        else:
            f = StringIO(self.dict[key])
            value = self.load(f, encoding=self.encodings[key])
        return value

    def __setitem__(self, key, value):
        encoding = None
        if isinstance(value, six.string_types):
            encoding = 'utf-8'
        self.encodings[key] = encoding
        if self.persist_path is not None:
            path = os.path.join(self.persist_path, '%s.pak' % key)
            with open(path, 'wb') as f:
                self.dump(value, f, encoding=encoding)
            self.dict[key] = path
        else:
            f = StringIO()
            self.dump(value, f, encoding=encoding)
            serialized = f.getvalue()
            self.dict[key] = serialized

    def __delitem__(self, key):
        if self.persist_path is not None:
            os.remove(self.dict[key])
        del self.dict[key]


def hash(obj, hash_name='md5'):
    """
    get a hash of a python object based on its serialized data
    """
    # TODO: avoid the double-serialization of pickling both for hashing and storage -- can accomplish by refactoring a hash&store method into pickledict
    # TODO OR find a faster way to hash?
    stream = io.BytesIO()
    dump = partial(msgpack.dump, default=msgpack_serialize)
    hasher = hashlib.new(hash_name)

    try:
        dump(obj, stream)
    except dill.PicklingError as e:
        e.args += ('PicklingError while hashing %r: %r' % (obj, e),)
        raise

    dumps = stream.getvalue()
    hasher.update(dumps)
    return hasher.hexdigest()
