import json
from nodebookcore import INDENT


def output_to_function(output_node, main_closing_statement, args):
    def add_dependencies(node_inputs, dep_set):
        dep = {(k, v) for k, v in node_inputs.iteritems() if k not in args and v is not None}
        return dep_set.union(dep)

    depends = add_dependencies(output_node.inputs, set())

    avail = set()
    funcs = [output_node.extract_function()]
    n = output_node
    while not depends.issubset(avail) and n.parent is not None:
        n = n.parent
        if len(depends.intersection(n.outputs.iteritems())) != 0:
            avail.update(n.outputs.iteritems())
            depends = add_dependencies(n.inputs, depends)
            funcs.append(n.extract_function())

    if n is None:
        raise KeyError('Could not find input dependencies: %s' % str(depends - avail))

    funcs = funcs[::-1]
    defs = "\n\n".join((f[0] for f in funcs))
    main = 'def main({}):'.format(','.join(args))
    for f in funcs:
        main += '\n{}{}'.format(INDENT, f[1])
    main += '\n{}{}'.format(INDENT, main_closing_statement)

    code = '{}\n\n{}\n'.format(defs, main)
    return code


def create_module(node, export_statement, input_dict):
    """
    create a python module to execute a given node
    """
    body = output_to_function(node, export_statement, input_dict.keys())

    imports = '\n'.join([
        'import json',
    ])

    deser = ''
    for k, v in input_dict.iteritems():
        deser += "\n{} = json.loads('{}')".format(k, json.dumps(v))
    deser += '\nmain({})'.format(','.join(input_dict.iterkeys()))

    code = '{}\n\n{}\n\n{}\n'.format(imports, body, deser)
    return code
