from app.app_restful import create_app


class FakeHandler:
    def __init__(self):
        self.last_payload = object()

    def start_simulation(self, payload):
        self.last_payload = payload
        return {"state": 0, "msg": "payload rejected"}

    def get_node_ipaddr(self, node_name):
        return {"node_name": node_name}


def test_malformed_start_json_returns_structured_error():
    handler = FakeHandler()
    client = create_app(handler).test_client()

    response = client.post(
        "/start",
        data='{"topology_type":',
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.is_json
    assert response.get_json() == {"state": 0, "msg": "payload rejected"}
    assert handler.last_payload is None


def test_get_route_tolerates_malformed_json_body():
    client = create_app(FakeHandler()).test_client()

    response = client.get(
        "/node/ipaddr",
        data="{",
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.get_json() == {"node_name": None}
