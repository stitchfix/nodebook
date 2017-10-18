# Nodebook

[![CircleCI](https://circleci.com/gh/stitchfix/nodebook.svg?style=shield)](https://circleci.com/gh/stitchfix/nodebook)

Nodebook is a plugin for Jupyter Notebook designed to enforce an ordered flow of cell execution. Conceptually, Nodebook notebooks operate like a script where each cell depends on the cells above it. This prevents messy and difficult to maintain out-of-order execution which frequently occurs in vanilla Jupyter notebooks where each cell modifies the global state. For more information, see [this post](http://multithreaded.stitchfix.com/blog/2017/07/26/nodebook/).


## Installation

Nodebook is available on pypi and can be installed with pip. Additionally, the jupyter extension must be registered:
```
pip install nodebook
jupyter nbextension install --py nodebook
```

## Usage

To use Nodebook, add the following lines to a cell in your Jupyter notebook:
```
#pragma nodebook off
%load_ext nodebook.ipython
%nodebook {mode} {name}
```
Where `{mode}` is one of `memory` or `disk`, and `{name}` is a unique identifier for your notebook.

Mode determines whether variables are stored in memory or on disk.

For additional example usage, see [nodebook_demo.ipynb](./nodebook_demo.ipynb). Also see below for a quick demo showing the basic difference in behavior between Nodebook and standard Jupyter:

![demo](https://user-images.githubusercontent.com/6323667/28484590-0935af6a-6e28-11e7-8bfa-f1555001bac4.gif)

## FAQ

#### Q: Should I use Python 2 or Python 3 with Nodebook?

There has been an [increasing consensus](http://www.python3statement.org/) toward sunsetting support for Python 2, including in Project Jupyter. Nodebook currently supports both Python 2 and Python 3, but Python 3 is preferred.

#### Q: Why am I seeing "ERROR:root:Cell magic `%%execute_cell` not found."?

Nodebook loads a javascript plugin to modify Jupyter's behavior. If you encounter this error, it means that the javascript plugin is loaded but the ipython plugin is not. This can happen when the javascript is already loaded but you have restarted the kernel and haven't run `%nodebook {mode} {name}`. The solution is either to run the `%nodebook` magic (if you want to run nodebook), or delete the cell with the `%nodebook` magic and refresh your browser to unload the javascript (if you want to turn nodebook off).

#### Q: What are the tradeoffs between memory and disk mode?

Nodebook serializes all cell outputs to maintain consistent state between cells. In `memory` mode, objects are serialized to an in-memory dictionary, in `disk` mode objects are serialized to a directory within your notebook's working directory. Speed can be a factor when choosing between them, but on a modern SSD, serialization time generally dominates and `memory` and `disk` mode have similar performance. The main consideration is that `disk` mode has the advantage of persisting your environment when the python kernel is restarted, but the disadvantage of leaving behind a directory on your local filesystem that you may want to manually clean up later (this can add up especially if you are working with large objects in your notebook).

#### Q: What are the limitations of Nodebook?

While Nodebook supports most Python operations, it has a few limitations related to the use of serialization. First, not all objects are currently serializable, most noteably generators. Second, serialization adds some extra time. This is imperceptible for small objects, but is noticable for objects larger than a few hundred MB. Instead of working directly with very large objects in Nodebook, I recommend using it to prototype your analysis on a subset of data.
