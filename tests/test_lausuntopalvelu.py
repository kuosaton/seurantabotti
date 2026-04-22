from __future__ import annotations

from unittest.mock import Mock

from clients.lausuntopalvelu import proposal_has_recipient


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
