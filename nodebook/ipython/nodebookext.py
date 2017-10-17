from __future__ import absolute_import
import six.moves.cPickle as pickle
import os
import sys
import errno

from nodebook.nodebookcore import Node, Nodebook, ReferenceFinder
from nodebook.pickledict import PickleDict

NODEBOOK_STATE = {
    "cache_dir": None,
    "nodebook": None,
}

MODE_DISK = "disk"
MODE_MEMORY = "memory"
ALLOWED_MODES = [MODE_DISK, MODE_MEMORY]


def nodebook(line):
    """
    ipython magic for initializing nodebook, expects name for nodebook database
    """
    args = line.lstrip().split(' ')

    try:
        mode = args[0]
        assert mode in ALLOWED_MODES
    except (IndexError, AssertionError):
        raise SyntaxError("Must specify mode as %s" % str(ALLOWED_MODES))

    if mode == MODE_MEMORY:
        persist = False
    else:
        persist = True

    if persist:
        NODEBOOK_STATE['cache_dir'] = 'nodebook_cache/'
        try:
            NODEBOOK_STATE['cache_dir'] += args[1]
        except IndexError:
            NODEBOOK_STATE['cache_dir'] += 'default'

        try:
            os.makedirs(NODEBOOK_STATE['cache_dir'])
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(NODEBOOK_STATE['cache_dir']):
                pass
            else:
                raise
        try:
            with open(os.path.join(NODEBOOK_STATE['cache_dir'], 'nodebook.p'), 'rb') as f:
                NODEBOOK_STATE['nodebook'] = pickle.load(f)
        except IOError:
            var_store = PickleDict(NODEBOOK_STATE['cache_dir'])
            NODEBOOK_STATE['nodebook'] = Nodebook(var_store)
    else:
        var_store = PickleDict()
        NODEBOOK_STATE['nodebook'] = Nodebook(var_store)

    if len(NODEBOOK_STATE['nodebook'].nodes) > 0:
        NODEBOOK_STATE['nodebook'].update_all_prompts(get_ipython().payload_manager)


def execute_cell(line, cell):
    """
    ipython magic for executing nodebook cell, expects cell id and parent id inline, followed by code
    """
    assert NODEBOOK_STATE['nodebook'] is not None, "Nodebook not initialized, please use %nodebook {nodebook_name}"
    cell_id, parent_id = line.lstrip().split(' ')

    # make sure cell exists and is in the right position
    NODEBOOK_STATE['nodebook'].insert_node_after(cell_id, parent_id)

    # update code and run
    NODEBOOK_STATE['nodebook'].update_code(cell_id, cell)
    res, objs = NODEBOOK_STATE['nodebook'].run_node(cell_id)

    # update prompts
    NODEBOOK_STATE['nodebook'].update_all_prompts(get_ipython().payload_manager)

    # update cache if needed
    if NODEBOOK_STATE['cache_dir'] is not None:
        with open(os.path.join(NODEBOOK_STATE['cache_dir'], 'nodebook.p'), 'wb') as f:
            pickle.dump(NODEBOOK_STATE['nodebook'], f, protocol=2)

    # UGLY HACK - inject outputs into global environment for autocomplete support
    # TODO: find a better way to handle autocomplete
    sys._getframe(2).f_globals.update(objs)
    return res


def load_ipython_extension(ipython):
    ipython.register_magic_function(nodebook, magic_kind='line')
    ipython.register_magic_function(execute_cell, magic_kind='cell')
    ipython.run_cell_magic('javascript', '', "Jupyter.utils.load_extensions('nodebook/nodebookext')")


def unload_ipython_extension(ipython):
    pass
