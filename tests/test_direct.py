import requests

from src.api import direct, webvpn
from src.runtime import config, fork_config


def test_portal_probe_is_answered_locally():
    probe = direct.DirectSession().get(config.WEBVPN_BASE + "/", allow_redirects=False)
    assert probe.status_code == 200


def test_origin_header_points_at_the_idp():
    session = direct.DirectSession()
    request = requests.Request(
        "POST", "https://x/y", headers={"Origin": config.WEBVPN_BASE, "Referer": "r"}
    )
    headers = session.prepare_request(request).headers
    assert headers["Origin"] == config.IDP_BASE and headers["Referer"] == "r"


def test_direct_mode_skips_webvpn(monkeypatch):
    monkeypatch.setattr(fork_config, "USE_WEBVPN", False)
    vpn = webvpn.WebVPNSession()
    assert isinstance(vpn.session, direct.DirectSession)
    assert vpn.logged_in and vpn.login()
    assert webvpn.get_vpn_url("https://icourse.fudan.edu.cn/a?b=1") == (
        "https://icourse.fudan.edu.cn/a?b=1"
    )


def test_saved_session_is_restored_when_still_valid(monkeypatch, tmp_path):
    monkeypatch.setattr(direct, "SESSION_FILE", str(tmp_path / "s.json"))
    old = requests.Session()
    old.cookies.set("PHPSESSID", "abc", domain="icourse.fudan.edu.cn", path="/")
    direct.save_session(old)

    ok = requests.Response()
    ok.status_code, ok._content = 200, b'{"code": 0}'
    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **k: ok)
    new = requests.Session()
    assert direct.restore_session(new, "https://x/infosimple")
    assert new.cookies.get("PHPSESSID") == "abc"


def test_stale_or_missing_session_is_not_restored(monkeypatch, tmp_path):
    monkeypatch.setattr(direct, "SESSION_FILE", str(tmp_path / "none.json"))
    assert not direct.restore_session(requests.Session(), "https://x/infosimple")

    monkeypatch.setattr(direct, "SESSION_FILE", str(tmp_path / "s.json"))
    direct.save_session(requests.Session())
    bad = requests.Response()
    bad.status_code, bad._content = 200, b'{"code": 401}'
    monkeypatch.setattr(requests.Session, "get", lambda self, *a, **k: bad)
    fresh = requests.Session()
    assert not direct.restore_session(fresh, "https://x/infosimple")
    assert not fresh.cookies


class _Reply:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def test_qr_login_returns_the_token_once_scanned(monkeypatch, tmp_path):
    monkeypatch.setattr(direct, "QR_FILE", str(tmp_path / "qr.jpg"))
    monkeypatch.setattr(direct.time, "sleep", lambda s: None)
    answers = iter(
        [
            _Reply({"data": {"qrMsg": "data:image/png;base64,eA==", "qrToken": "t"}}),
            _Reply({"code": 4001}),  # not scanned yet
            _Reply({"code": 200, "loginToken": "TOKEN"}),
        ]
    )
    session = type("S", (), {"post": lambda self, *a, **k: next(answers)})()
    got = direct.qr_login(
        session,
        lambda u: u,
        {},
        {"entityId": "e"},
        {"authChainCode": "c", "requestNumber": "n"},
    )
    assert got == "TOKEN" and (tmp_path / "qr.jpg").read_bytes() == b"x"
