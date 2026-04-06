from apps.installed_apps.old_graph import (
    configure_old_graph_launch,
    old_graph,
    reset_old_graph_launch,
)


def graph(db={}):
    configure_old_graph_launch(
        entry_target=("graph", "root"),
        back_target=("home", "root"),
    )
    try:
        return old_graph(db)
    finally:
        reset_old_graph_launch()
