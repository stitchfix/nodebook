from __future__ import absolute_import
from __future__ import print_function
from . import pickledict
import ast
import six.moves.builtins
import six

INDENT = '    '  # an indent is canonically 4 spaces ;)


class ReferenceFinder(ast.NodeVisitor):
    def __init__(self):
        self.locals = set()
        self.inputs = set()
        self.imports = set()

    def visit_Assign(self, node):
        # we need to visit "value" before "targets"
        self.visit(node.value)
        for target in node.targets:
            self.visit(target)

    def generic_comp(self, node):
        # we need to visit generators before elt
        for generator in node.generators:
            self.visit(generator)
        self.visit(node.elt)

    def visit_ListComp(self, node):
        return self.generic_comp(node)

    def visit_SetComp(self, node):
        return self.generic_comp(node)

    def visit_GeneratorExp(self, node):
        return self.generic_comp(node)

    def visit_DictComp(self, node):
        # we need to visit generators before key/value
        for generator in node.generators:
            self.visit(generator)
        self.visit(node.value)
        self.visit(node.key)

    def visit_FunctionDef(self, node):
        self.locals.add(node.name)
        self.generic_visit(node)

    def visit_arg(self, node):
        self.locals.add(node.arg)

    def visit_AugAssign(self, node):
        target = node.target
        while (type(target) is ast.Subscript):
            target = target.value
        if target.id not in self.locals:
            self.inputs.add(target.id)
        self.generic_visit(node)

    def visit_Name(self, node):
        if type(node.ctx) in {ast.Store, ast.Param}:
            self.locals.add(node.id)
        elif type(node.ctx) is ast.Load:
            if node.id not in self.locals:
                self.inputs.add(node.id)

    def visit_alias(self, node):
        self.imports.add(node.name)
        if node.asname is not None:
            self.locals.add(node.asname)
        else:
            self.locals.add(node.name)


class Nodebook(object):
    """
    Nodebook maintains a variable store for accessing variables and a pointer to the head node in the list
    """

    def __init__(self, variable_store):
        self.variables = variable_store
        self.refcount = {}
        self.head = None
        self.nodes = {}

    def add_ref(self, val_hash):
        """
        Increment reference count for value hash
        """
        self.refcount[val_hash] = self.refcount.get(val_hash, 0) + 1

    def remove_ref(self, val_hash):
        """
        Decrement reference count for value hash
        """
        self.refcount[val_hash] -= 1
        if self.refcount[val_hash] == 0:
            del self.variables[val_hash]

    def update_code(self, node_id, code):
        """
        Update target node's code
        """
        node = self.nodes[node_id]
        node.update_code(code)

    def run_node(self, node_id):
        """
        Run target node and retrieve expression result and modified objects
        """
        # get node inputs
        node = self.nodes[node_id]
        input_objs = {}
        input_hashes = {}
        for var in node.inputs.keys():
            val_hash = self._find_latest_output(node.parent, var)
            if val_hash is not None:
                input_objs[var] = self.variables[val_hash]
                input_hashes[var] = val_hash

        # run node
        res, output_objs, output_hashes = node.run(input_objs, input_hashes)

        # update node outputs
        for var, val in six.iteritems(output_objs):
            self.variables[output_hashes[var]] = val
        self._update_output_hashes(node, output_hashes)

        return res, output_objs

    def _find_latest_output(self, node, var):
        """
        Find the most recent output hash for a variable starting from node
        Fails if undefined unless var is a builtin
        """
        # base case
        if node is None:
            if var in six.moves.builtins.__dict__:
                return None
            else:
                raise KeyError("name '%s' is not defined" % var)

        if var in node.outputs:
            # found it, but make sure we're valid
            if node.valid:
                return node.outputs[var]
            else:
                # re-run the parent if it wasn't valid
                # TODO: synchronize output with frontend javascript
                print("auto-running invalidated node N_%s (%s)" % (node.get_index() + 1, node.name))
                self.run_node(node.name)
                return self._find_latest_output(node, var)
        else:
            # check next parent
            return self._find_latest_output(node.parent, var)

    def _update_output_hashes(self, node, outputs):
        """
        Update node's output hashes and invalid downstream nodes that depended on their previous values
        """
        # invalidate any any children relying on specific hash-versions of old outputs that aren't in the new outputs
        invalidated_outputs = set(six.iteritems(node.outputs)) - set(six.iteritems(outputs))
        invalidated_outputs = {k: v for k, v in invalidated_outputs}

        # also invalidate any children that rely on any version of a brand-new output, regardless of hash
        # TODO this is potentially overly restrictive, if, eg, a value is blindly over-written again later
        # TODO(con't) we should try to account for this to avoid invalidating excessively many cells
        new_outputs = set(six.iteritems(outputs)) - set(six.iteritems(node.outputs))
        new_outputs = {k: v for k, v in new_outputs}

        # update reference counts
        for val_hash in six.itervalues(new_outputs):
            self.add_ref(val_hash)
        for val_hash in six.itervalues(invalidated_outputs):
            self.remove_ref(val_hash)

        # invalidate changed outputs
        invalidated_outputs.update({k: None for k, _ in six.iteritems(new_outputs)})
        node.outputs = outputs
        node.invalidate_children(invalidated_outputs)

    def insert_node_after(self, node_id, parent_id):
        """
        Create node with id node_id if it doesn't exist, then move it to a position after parent_id
        """
        # get the node by id or make a new node
        if node_id in self.nodes:
            node = self.nodes[node_id]
        else:
            node = Node(node_id)
            self.nodes[node_id] = node

        # get the parent by id or leave empty
        parent = self.nodes.get(parent_id, None)

        if parent is None:
            # no parent, node is head
            if self.head != node:
                node.child = self.head
                self.head = node
        elif parent == node.parent:
            # node is already in the right place, don't need to do anything
            pass
        else:
            # first, extract node from its current position
            old_parent = node.parent
            old_child = node.child
            if old_parent is not None:
                old_parent.child = old_child
            if old_child is not None:
                old_child.parent = old_parent

            # next, insert node to its new location
            node.parent = parent
            if parent is not None:
                # put node in between target parent and parent's old child
                node.child = parent.child
                parent.child = node
                # if node now has a child, set it as child's parent
                if node.child is not None:
                    node.child.parent = node

    def update_all_prompts(self, ipython_payload_manager):
        """
        Update prompts for all nodes based on their position in list
        """
        node = self.head
        index = 1
        while node is not None:
            if not node.valid:
                prompt = "X"
            else:
                prompt = "N_%d" % index
            self.update_prompt(node, prompt, ipython_payload_manager)
            node = node.child
            index += 1

    def update_prompt(self, node, prompt, ipython_payload_manager):
        """
        Use ipython payload manager to update prompt for target node
        """
        payload = {
            "source": "set_prompt",
            "cell_id": node.name,
            "prompt": prompt,
        }
        ipython_payload_manager.write_payload(payload, single=False)


class Node(object):
    def __init__(self, name):
        self.name = name
        self.parent = None
        self.child = None
        self.valid = True
        self.inputs = {}
        self.outputs = {}
        self.imports = set()
        self.code = ''

    def update_code(self, code):
        """
        Parse a block of python code for its inputs and assign to this node
        """
        self.code = code
        tree = ast.parse(code)
        rf = ReferenceFinder()
        rf.visit(tree)
        self.inputs = {x: None for x in rf.inputs}
        self.imports = rf.imports
        self.valid = False  # not valid until executed

    def run(self, input_objs, input_hashes):
        """
        Execute this node in the provided environment given hashes of inputs
        """
        env = input_objs

        # if code ends in an expression, execute it as an expression, otherwise execute whole block
        block = ast.parse(self.code)
        if len(block.body) > 0 and type(block.body[-1]) is ast.Expr:
            last = ast.Expression(block.body.pop().value)
            exec(compile(block, '<string>', mode='exec'), env)
            res = eval(compile(last, '<string>', mode='eval'), env)
        else:
            exec(compile(block, '<string>', mode='exec'), env)
            res = None

        # find outputs which have changed from input hashes
        self.inputs = input_hashes
        output_objs = {}
        output_hashes = {}
        for var in [k for k in env.keys() if k != '__builtins__']:
            val = env[var]
            val_hash = pickledict.hash(val)
            if self.inputs.get(var, 0) != val_hash:
                output_hashes[var] = val_hash
                output_objs[var] = val
        self.valid = True
        return res, output_objs, output_hashes

    def get_index(self):
        """
        Return index of this node
        """
        if self.parent is None:
            return 0
        else:
            return 1 + self.parent.get_index()

    def invalidate_children(self, outputs):
        """
        Invalidate any children of this node that depend on the provided outputs
        """
        if len(outputs) == 0:
            return  # no action for empty outputs

        child = self.child
        while child is not None:
            child.invalidate(outputs)
            child = child.child

    def invalidate(self, inputs=None):
        """
        Invalidate node and any children that depend on its outputs
        Optionally conditional on this node using a specific input variable / hash
        """
        # only need to take action if this node _was_ valid
        if not self.valid:
            return

        # don't invalidate if input var is specified and is not one of our inputs
        if inputs is not None:
            shared_inputs = set(inputs).intersection(self.inputs)
            if len(shared_inputs) == 0:
                return

            # also don't invalidate if no specified input hashes match
            input_match = False
            for input in shared_inputs:
                if inputs[input] is None or inputs[input] == self.inputs[input]:
                    input_match = True
            if not input_match:
                return

        self.valid = False

        # also invalidate children that rely on our outputs
        self.invalidate_children(self.outputs)

    def __str__(self):
        return self.name
