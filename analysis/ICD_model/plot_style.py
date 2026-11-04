"""Shared figure style and export for the manuscript notebooks.

Every figure is drawn in Helvetica and written to ``plots/<notebook>/<name>.svg`` and
``plots/<notebook>/<name>.png`` (600 dpi), with ``plots/`` at the repository root.

    import plot_style
    plot_style.setup("01_analysis_boolean_core")
    ...
    plot_style.save_fig(fig, "truth_table")            # matplotlib figure
    plot_style.save_graph(A, "full_network", "dot")    # pygraphviz AGraph

Import it before any ``os.chdir`` in the notebook: the output folder is resolved from this
file's location, so later changes of working directory do not move it.

Graphviz layouts are kept identical from run to run by two things done here: importing this
module puts the graphviz installed with the running Python first on ``PATH`` (pygraphviz runs
whichever ``dot`` it finds there, and other versions lay graphs out differently), and
``stable_subgraph`` replaces ``g.subgraph(nodes)`` for any graph that is drawn.
"""
import os
import sys
from contextlib import contextmanager
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

FONT = "Helvetica"
DPI = 600
PLOTS_DIR = Path(__file__).resolve().parents[1] / "plots"

_env_bin = str(Path(sys.executable).parent)
if (Path(_env_bin) / "dot").exists() and os.environ.get("PATH", "").split(os.pathsep)[0] != _env_bin:
    os.environ["PATH"] = os.pathsep.join([_env_bin, os.environ.get("PATH", "")])

_out_dir = None


def setup(notebook):
    """Set Helvetica as the matplotlib font and create ``plots/<notebook>/``."""
    global _out_dir
    mpl.rcParams.update({
        # DejaVu Sans only supplies glyphs Helvetica lacks (e.g. → and ⊣); the fallback needs the
        # families listed here explicitly, not via the generic "sans-serif"
        "font.family": [FONT, "DejaVu Sans"],
        "font.sans-serif": [FONT, "DejaVu Sans"],   # used by networkx labels (font_family="sans-serif")
        "mathtext.fontset": "custom",
        "mathtext.rm": FONT,
        "mathtext.it": f"{FONT}:italic",
        "mathtext.bf": f"{FONT}:bold",
        "svg.fonttype": "none",     # keep text as text in the SVG, so labels stay editable
        "pdf.fonttype": 42,
        "svg.hashsalt": "plot_style",   # fixed SVG element ids, so an unchanged figure gives an unchanged file
    })
    _out_dir = PLOTS_DIR / notebook
    _out_dir.mkdir(parents=True, exist_ok=True)
    return _out_dir


def _path(name, ext):
    if _out_dir is None:
        raise RuntimeError("call plot_style.setup(<notebook name>) first")
    return _out_dir / f"{name}.{ext}"


def save_fig(fig, name):
    """Write a matplotlib figure as SVG and 600-dpi PNG."""
    fig.savefig(_path(name, "svg"), dpi=DPI, bbox_inches="tight", metadata={"Date": None})
    fig.savefig(_path(name, "png"), dpi=DPI, bbox_inches="tight")


def save_gif(anim, name, fps=20, dpi=100):
    """Write a matplotlib animation as a GIF and return its path."""
    from matplotlib.animation import PillowWriter

    path = _path(name, "gif")
    anim.save(path, writer=PillowWriter(fps=fps), dpi=dpi)
    return path


@contextmanager
def save_shown(name):
    """Save the figure a library function shows itself (and does not return) under `name`."""
    show = plt.show

    def save_then_show(*args, **kwargs):
        save_fig(plt.gcf(), name)
        show(*args, **kwargs)

    plt.show = save_then_show
    try:
        yield
    finally:
        plt.show = show


def stable_subgraph(g, nodes):
    """Copy of the subgraph of networkx graph `g` induced by `nodes`, in `g`'s node and edge order.

    ``g.subgraph(nodes)`` iterates small subgraphs in set order, which changes with Python's
    per-process hash seed; dot breaks ties by insertion order, so the layout would change too.
    """
    keep = set(nodes)
    h = g.__class__()
    h.graph.update(g.graph)
    h.add_nodes_from((v, g.nodes[v]) for v in g if v in keep)
    h.add_edges_from((a, b, d) for a, b, d in g.edges(data=True) if a in keep and b in keep)
    return h


def use_helvetica(A):
    """Default every graph, cluster, node and edge label of a pygraphviz AGraph to Helvetica."""
    for attrs in (A.graph_attr, A.node_attr, A.edge_attr):
        if not attrs.get("fontname"):
            attrs["fontname"] = FONT
    return A


def save_graph(A, name, prog="dot", args=""):
    """Lay out a pygraphviz AGraph with `prog` and write it as SVG and 600-dpi PNG."""
    use_helvetica(A)
    A.draw(str(_path(name, "svg")), format="svg", prog=prog, args=args)
    A.draw(str(_path(name, "png")), format="png", prog=prog, args=f"{args} -Gdpi={DPI}".strip())
