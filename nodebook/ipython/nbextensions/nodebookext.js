define([
    'base/js/namespace',
    'notebook/js/codecell',
    'notebook/js/notebook'
    ],
    function(
        IPython,
        codecell,
        notebook
    ){
    var CodeCell = codecell.CodeCell;
    var Notebook = notebook.Notebook;

    function _on_load(){
        console.info('[Nodebook] Extension loaded')
        // currently we reinitialze all cells on import
        // TODO: allow recovery of previously defined state
        var cells = IPython.notebook.get_cells();
        var name_count = 0;
        for(var i in cells){
            var cell = cells[i];
            if ((cell instanceof IPython.CodeCell)) {
                if ("node_name" in cell.metadata) {
                    cell.cell_id = cell.metadata["node_name"]
                } else {
                    cell.metadata["node_exists"] = false;
                    cell.metadata["node_name"] = cell.cell_id;
                }
            }
        }

        function handle_test_payload(payload) {
            var cells = this.notebook.get_cells();
            var cell_by_id = cells.find(function(cell, index){return cell.cell_id == payload['cell_id']});

            try {
                cell_by_id.set_input_prompt(payload['prompt'])
            } catch(err) {
                console.log(err)
            }
        }

        function patch_CodeCell_execute () {
            console.info('[Nodebook] Patching cell execute')
            CodeCell.prototype.execute = function (stop_on_error) {
                if (!this.kernel) {
                    console.log("Can't execute cell since kernel is not set.");
                    return;
                }

                if (stop_on_error === undefined) {
                    stop_on_error = true;
                }

                this.output_area.clear_output(false, true);
                var old_msg_id = this.last_msg_id;
                if (old_msg_id) {
                    this.kernel.clear_callbacks_for_msg(old_msg_id);
                    delete CodeCell.msg_cells[old_msg_id];
                    this.last_msg_id = null;
                }
                if (this.get_text().trim().length === 0) {
                    // nothing to do
                    this.set_input_prompt(null);
                    return;
                }
                this.set_input_prompt('*');
                this.element.addClass("running");


                ////// MODIFIED SECTION
                var callbacks = this.get_callbacks();

                // add in an extra callback here -- probably not the best place though
                callbacks['shell']['payload']['set_prompt'] = $.proxy(handle_test_payload, this);


                // first get any pragmas
                var my_code = this.get_text();
                if (my_code.substr(0, 16) == "#pragma nodebook") {
                    var pragma_arg = my_code.split("\n")[0].substr(17);
                } else {
                    var pramga_arg = null;
                }

                if (pragma_arg == "off") {
                    console.log("Running outside nodebook");
                    var exec_text = my_code
                    this.metadata["node_exists"] = false;
                } else {
                    // find id of this cell and the previous code cell
                    var node_name = this.cell_id;
                    var index = this.notebook.find_cell_index(this);

                    // find the first previous non-empty code cell
                    do {
                        index--;
                        parent = this.notebook.get_cell(index);
                        is_valid = (parent instanceof IPython.CodeCell) && (parent.metadata['node_exists'] == true)
                    }
                    while ((index > 0) && !is_valid);
                    var parent_name = parent.cell_id;
                    if (index == 0 && !is_valid) {
                        // no valid parent found
                        parent_name = "";
                    }

                    // put ipython cell magics first (mostly for %%time)
                    if (my_code.startsWith('%%')) {
                        var split_code = my_code.split('\n');
                        var external_magic = split_code.shift();
                        external_magic = external_magic.concat('\n');
                        my_code = split_code.join('\n');
                    } else {
                        var external_magic = "";
                    }

                    var nodebook_magic = "%%execute_cell  ".concat(node_name, " ", parent_name, "\n");
                    var exec_text = nodebook_magic.concat(my_code);
                    exec_text = external_magic.concat(exec_text);

                    // mark as existing
                    this.metadata["node_name"] = this.cell_id;
                    this.metadata["node_exists"] = true;
                }
                this.last_msg_id = this.kernel.execute(exec_text, callbacks, {silent: false, store_history: true,
                    stop_on_error : stop_on_error});
                ////// END MODIFIED SECTION

                CodeCell.msg_cells[this.last_msg_id] = this;
                this.render();
                this.events.trigger('execute.CodeCell', {cell: this});
                var that = this;
                function handleFinished(evt, data) {
                    if (that.kernel.id === data.kernel.id && that.last_msg_id === data.msg_id) {
                            that.events.trigger('finished_execute.CodeCell', {cell: that});
                        that.events.off('finished_iopub.Kernel', handleFinished);
                    }
                }
                this.events.on('finished_iopub.Kernel', handleFinished);
            };
        }

        patch_CodeCell_execute()
    }


    return {load_ipython_extension: _on_load };
})