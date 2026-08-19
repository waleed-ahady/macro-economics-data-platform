from pathlib import Path

from macro_data_platform.services.ingestion import load_world_bank_config


def test_default_catalog_is_multi_country_and_macro_focused() -> None:
    config = load_world_bank_config(Path("configs/world_bank.yml"))
    assert len(config.countries) == 14
    assert len(config.indicators) == 11
    assert {item.code for item in config.indicators} >= {
        "gdp_growth",
        "gdp_per_capita",
        "inflation",
        "unemployment_rate",
        "current_account_balance",
    }
