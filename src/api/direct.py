"""Direct mode (``USE_WEBVPN=0``): talk to icourse/id.fudan.edu.cn without WebVPN.

``install`` swaps the WebVPN session for one that answers the WebVPN-only steps
locally, so the unmodified ``WebVPNSession.authenticate_icourse`` flow runs as is.
"""

import requests

from src.runtime import config


class DirectSession(requests.Session):
    """Session with a canned WebVPN portal probe and the IDP as ``Origin``."""

    def prepare_request(self, request):
        """Point the WebVPN ``Origin`` at the IDP."""
        prepared = super().prepare_request(request)
        if prepared.headers.get("Origin") == config.WEBVPN_BASE:
            prepared.headers["Origin"] = config.IDP_BASE
        return prepared

    def send(self, request, **kwargs):
        """Answer the WebVPN portal probe without touching the network."""
        if request.url == config.WEBVPN_BASE + "/":  # "is the portal session hot?"
            probe = requests.Response()
            probe.status_code = 200
            probe.url = request.url
            return probe
        return super().send(request, **kwargs)


def install(vpn) -> None:
    """Make ``vpn`` (a ``WebVPNSession``) work without the WebVPN portal."""
    session = DirectSession()
    session.headers.update(vpn.session.headers)
    vpn.session = session
    vpn.logged_in = True
    vpn.login = lambda *args, **kwargs: True  # there is no portal login to do
