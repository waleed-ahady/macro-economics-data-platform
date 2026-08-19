import httpx

from macro_data_platform.clients.world_bank import WorldBankClient, parse_world_bank_value


def test_world_bank_client_uses_v2_indicator_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/country/USA;DEU/indicator/FP.CPI.TOTL.ZG")
        assert request.url.params["format"] == "json"
        assert request.url.params["date"] == "2020:2024"
        return httpx.Response(
            200,
            json=[
                {"page": 1, "pages": 1, "total": 2},
                [
                    {"countryiso3code": "USA", "date": "2024", "value": 2.9},
                    {"countryiso3code": "DEU", "date": "2024", "value": 2.3},
                ],
            ],
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = WorldBankClient(client=http_client)
    records = client.get_indicator_observations(
        "FP.CPI.TOTL.ZG",
        ["USA", "DEU"],
        start_year=2020,
        end_year=2024,
    )
    assert len(records) == 2
    assert records[1]["countryiso3code"] == "DEU"


def test_world_bank_value_parser() -> None:
    assert parse_world_bank_value(None) is None
    assert parse_world_bank_value("12.5") == 12.5
