"""Direct mode (``USE_WEBVPN=0``): talk to icourse/id.fudan.edu.cn without WebVPN.

``install`` swaps the WebVPN session for one that answers the WebVPN-only steps
locally, so the unmodified ``WebVPNSession.authenticate_icourse`` flow runs as is.

The same module also holds the fork's login extras: the QR second factor the IDP now
demands (``qr_login``).
"""

import base64
import os
import time

import requests

from src.runtime import config

QR_FILE = os.path.join("temp", "qr.jpg")
QR_WAIT_S = 120


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


def qr_login(session, url_of, headers, payload, reply) -> str:
    """Finish the IDP's second factor with a QR scan; return the ``loginToken``.

    ``payload``/``reply`` are the password step's request and answer.  The QR image is
    written to ``QR_FILE``; scan it with the Fudan app within ``QR_WAIT_S`` seconds.
    """
    base = f"{config.IDP_BASE}/idp/authn"
    deadline = time.time() + QR_WAIT_S
    while time.time() < deadline:  # a code lives only ~30 s, so refresh it when it dies
        # No ``lck`` here: with it the IDP marks the new code as expired at once.
        made = session.post(
            url_of(base + "/getAuthQr"),
            json={"entityId": payload["entityId"]},
            headers=headers,
            timeout=60,
        ).json()
        qr = made["data"]
        os.makedirs(os.path.dirname(QR_FILE), exist_ok=True)
        with open(QR_FILE, "wb") as f:
            f.write(base64.b64decode(qr["qrMsg"].split(",", 1)[1]))
        print(
            f"[QR] Scan {os.path.abspath(QR_FILE)} with the Fudan app "
            f"({time.strftime('%H:%M:%S')}, valid ~30s)...",
            flush=True,
        )
        body = {
            **payload,
            "authModuleCode": "qr",
            "authChainCode": reply["authChainCode"],
            "requestNumber": reply["requestNumber"],
            "authPara": {"qrToken": qr["qrToken"]},
        }
        while time.time() < deadline:
            time.sleep(2)
            got = session.post(
                url_of(base + "/authExecute"), json=body, headers=headers, timeout=60
            ).json()
            if got.get("loginToken"):
                return got["loginToken"]
            if got.get("code") == 4005:  # "二维码已失效": ask for a fresh one
                break
    raise RuntimeError("QR code was not scanned in time")
