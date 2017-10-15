from __future__ import absolute_import
import pandas as pd
import pytest
from nodebook.nodebookcore import ReferenceFinder, Nodebook, Node
from nodebook.pickledict import PickleDict
import ast


class TestReferenceFinder(object):
    @pytest.fixture()
    def rf(self):
        return ReferenceFinder()

    def test_assign(self, rf):
        code_tree = ast.parse("x = 3")
        rf.visit(code_tree)
        assert rf.inputs == set()
        assert rf.imports == set()
        assert rf.locals == {'x'}

    def test_augassign(self, rf):
        code_tree = ast.parse("x += 3")
        rf.visit(code_tree)
        assert rf.inputs == {'x'}
        assert rf.imports == set()
        assert rf.locals == {'x'}

    def test_import(self, rf):
        code_tree = ast.parse("import numpy as np")
        rf.visit(code_tree)
        assert rf.inputs == set()
        assert rf.imports == {'numpy'}
        assert rf.locals == {'np'}

    def test_multiline(self, rf):
        code_tree = ast.parse(
            "import pandas as pd\n"
            "y = pd.Series(x)\n"
        )
        rf.visit(code_tree)
        assert rf.inputs == {'x'}
        assert rf.locals == {'pd', 'y'}
        assert rf.imports == {'pandas'}


class TestNodebook(object):
    @pytest.fixture()
    def nb(self):
        var_store = PickleDict()
        return Nodebook(var_store)

    def test_single_node(self, nb):
        node_id = '111'
        nb.insert_node_after(node_id, None)
        nb.update_code(node_id, "x = 42\nx")
        res, objs = nb.run_node(node_id)
        assert res == 42
        assert objs == {'x': 42}

    def test_node_chain(self, nb):
        # first node sets x to 42
        node_id1 = '111'
        nb.insert_node_after(node_id1, None)
        nb.update_code(node_id1, "x = 42")
        res, objs = nb.run_node(node_id1)
        assert res == None
        assert objs == {'x': 42}

        # second node increments x to 52
        node_id2 = '222'
        nb.insert_node_after(node_id2, node_id1)
        nb.update_code(node_id2, "x += 10")
        res, objs = nb.run_node(node_id2)
        assert res == None
        assert objs == {'x': 52}

        # running second node again should give same results
        res, objs = nb.run_node(node_id2)
        assert res == None
        assert objs == {'x': 52}

        # third node evaluates to x
        node_id3 = '333'
        nb.insert_node_after(node_id3, node_id2)
        nb.update_code(node_id3, "x")
        res, objs = nb.run_node(node_id3)
        assert res == 52
        assert objs == {}

        # fourth node inserted between first and second node, changing x to 1
        node_id4 = '444'
        nb.insert_node_after(node_id4, node_id1)
        nb.update_code(node_id4, "x=1")
        res, objs = nb.run_node(node_id4)
        assert res == None
        assert objs == {'x': 1}

        # re-running third node should now evaluate to 11
        res, objs = nb.run_node(node_id3)
        assert res == 11
        assert objs == {}
