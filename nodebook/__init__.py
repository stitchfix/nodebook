def _jupyter_nbextension_paths():
    """
    Jupyter nbextension location
    """
    return [dict(
        section="notebook",
        src="ipython/nbextensions",
        # directory in the `nbextension/` namespace
        dest="nodebook",
        # _also_ in the `nbextension/` namespace
        require="nodebook/nodebookext")]