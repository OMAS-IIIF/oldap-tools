"""Connection construction for trusted direct OLDAP administration.

`oldap-tools` authenticates directly against the configured GraphDB repository.
It needs the resulting authorization context but never exposes an OLDAP bearer
token, so access-token issuance is deliberately disabled.
"""

from oldaplib.src.connection import Connection


def create_connection(
    *,
    graphdb_base: str,
    repo: str,
    user: str,
    password: str,
    graphdb_user: str | None = None,
    graphdb_password: str | None = None,
    context_name: str | None = None,
) -> Connection:
    """Create an authenticated direct connection without issuing a JWT.

    Args:
        graphdb_base: Base URL of the GraphDB server.
        repo: GraphDB repository name.
        user: OLDAP user identifier used for authorization.
        password: OLDAP user password.
        graphdb_user: Optional GraphDB HTTP Basic Auth user.
        graphdb_password: Optional GraphDB HTTP Basic Auth password.
        context_name: Optional OLDAP context name.

    Returns:
        An authenticated connection with an authorization context and no
        access token.

    Raises:
        OldapError: If GraphDB cannot be reached or authentication fails.
    """
    connection_options = {
        "server": graphdb_base,
        "repo": repo,
        "dbuser": graphdb_user,
        "dbpassword": graphdb_password,
        "userId": user,
        "credentials": password,
        "issue_access_token": False,
    }
    if context_name is not None:
        connection_options["context_name"] = context_name
    return Connection(**connection_options)
