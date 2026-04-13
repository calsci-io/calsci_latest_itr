from .hub import GroupHubApp


def create_app(manifest):
    return GroupHubApp(manifest)
