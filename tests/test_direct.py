import requests

from src.api import direct, webvpn
from src.runtime import config, fork_config


def test_portal_probe_is_answered_locally():
    probe = direct.DirectSession().get(config.WEBVPN_BASE + "/", allow_redirects=False)
    assert probe.status_code == 200


def test_origin_header_points_at_the_idp():
    session = direct.DirectSession()
    request = requests.Request(
        "POST", "https://x/y", headers={"Origin": config.WEBVPN_BASE, "Referer": "r"})
    headers = session.prepare_request(request).headers
    assert headers["Origin"] == config.IDP_BASE and headers["Referer"] == "r"


def test_direct_mode_skips_webvpn(monkeypatch):
    monkeypatch.setattr(fork_config, "USE_WEBVPN", False)
    vpn = webvpn.WebVPNSession()
    assert isinstance(vpn.session, direct.DirectSession)
    assert vpn.logged_in and vpn.login()
    assert webvpn.get_vpn_url("https://icourse.fudan.edu.cn/a?b=1") == (
        "https://icourse.fudan.edu.cn/a?b=1")
