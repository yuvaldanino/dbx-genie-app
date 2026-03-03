"""FastAPI dependency injection convenience wrappers."""

from ._defaults import ConfigDependency, ClientDependency, UserWorkspaceClientDependency
from ._headers import HeadersDependency


class Dependencies:
    """FastAPI dependency injection convenience wrappers."""

    Config = ConfigDependency
    Client = ClientDependency
    UserClient = UserWorkspaceClientDependency
    Headers = HeadersDependency
