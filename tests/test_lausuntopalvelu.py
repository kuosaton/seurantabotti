from __future__ import annotations

from unittest.mock import Mock

from clients.lausuntopalvelu import get_participation_flags, proposal_has_recipient


def test_proposal_has_recipient_from_jakelu_table() -> None:
    html = """
    <html><body>
      <h5>Jakelu:</h5>
      <div class="common-information-text-container">
        <table class="answered-participant">
          <tr><td>Akava ry</td></tr>
          <tr><td>Kuluttajaliitto ry</td></tr>
        </table>
      </div>
    </body></html>
    """
    response = Mock()
    response.text = html
    response.raise_for_status.return_value = None

    client = Mock()
    client.get.return_value = response

    assert proposal_has_recipient(client, "abc", "Kuluttajaliitto ry") is True


def test_proposal_has_recipient_fallback_region() -> None:
    html = """
    <html><body>
      <div id="listOfRespondentsSettingsBody">
        <p>Jakelu</p>
        <span>Elinkeinoelaman keskusliitto EK ry</span>
        <span>Kuluttajaliitto ry</span>
      </div>
    </body></html>
    """
    response = Mock()
    response.text = html
    response.raise_for_status.return_value = None

    client = Mock()
    client.get.return_value = response

    assert proposal_has_recipient(client, "abc", "kuluttajaliitto ry") is True


def test_proposal_has_recipient_false_when_not_found() -> None:
    response = Mock()
    response.text = "<html><body><div>No recipients here</div></body></html>"
    response.raise_for_status.return_value = None

    client = Mock()
    client.get.return_value = response

    assert proposal_has_recipient(client, "abc", "Kuluttajaliitto ry") is False


def test_proposal_has_recipient_matches_kuluttajaliitto_typo_with_prefix_lookup() -> None:
    html = """
    <html><body>
      <h5>Jakelu:</h5>
      <div>
        <table>
          <tr><td>kuluttajaliito - Konsumentforbundet ry</td></tr>
        </table>
      </div>
    </body></html>
    """
    response = Mock()
    response.text = html
    response.raise_for_status.return_value = None

    client = Mock()
    client.get.return_value = response

    assert proposal_has_recipient(client, "abc", "Kuluttajaliit") is True


def test_get_participation_flags_detects_responded() -> None:
    html = """
    <html><body>
      <h5>Jakelu:</h5>
      <div><table class="answered-participant">
        <tr><td>Akava ry</td></tr>
      </table></div>
      <script>
        "UsersWhoAnswered":[{"DisplayName":"Kuluttajaliitto ry","Organization":"Kuluttajaliitto ry"}]
      </script>
    </body></html>
    """
    response = Mock()
    response.text = html
    response.raise_for_status.return_value = None
    client = Mock()
    client.get.return_value = response

    in_jakelu, has_responded = get_participation_flags(client, "abc", "Kuluttajaliit")
    assert in_jakelu is False
    assert has_responded is True


def test_get_participation_flags_both_false_when_absent() -> None:
    response = Mock()
    response.text = '<html><body>"UsersWhoAnswered":[]</body></html>'
    response.raise_for_status.return_value = None
    client = Mock()
    client.get.return_value = response

    in_jakelu, has_responded = get_participation_flags(client, "abc", "Kuluttajaliit")
    assert in_jakelu is False
    assert has_responded is False


def test_get_participation_flags_single_fetch() -> None:
    response = Mock()
    response.text = '<html><body>"UsersWhoAnswered":[]</body></html>'
    response.raise_for_status.return_value = None
    client = Mock()
    client.get.return_value = response

    get_participation_flags(client, "xyz", "Kuluttajaliit")
    assert client.get.call_count == 1
