import os
from datetime import date
from typing import Any

import httpx
import pandas as pd
import plotly.express as px
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
CURRENT_YEAR = date.today().year

st.set_page_config(
    page_title="Global Macroeconomic Explorer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px;}
      [data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.20); border-radius: 12px; padding: 14px 16px;}
      [data-testid="stMetricLabel"] {font-size: .9rem;}
      div[data-testid="stDataFrame"] {border: 1px solid rgba(128,128,128,.16); border-radius: 10px; overflow: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Global Macroeconomic Explorer")
st.caption(
    "Compare long-run economic indicators across major economies using standardized World Bank data."
)


@st.cache_data(ttl=120, show_spinner=False)
def api_get(path: str, params: tuple[tuple[str, Any], ...] = ()) -> dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(f"{API_BASE_URL}{path}", params=list(params))
        response.raise_for_status()
        return dict(response.json())


def request(
    path: str,
    params: dict[str, Any] | list[tuple[str, Any]] | None = None,
) -> dict[str, Any]:
    if params is None:
        encoded: tuple[tuple[str, Any], ...] = ()
    elif isinstance(params, dict):
        encoded = tuple((key, value) for key, value in params.items() if value is not None)
    else:
        encoded = tuple(params)
    return api_get(path, encoded)


def format_value(value: float | None, units: str | None) -> str:
    if value is None:
        return "—"
    unit_text = (units or "").lower()
    if "percent" in unit_text:
        return f"{value:,.2f}%"
    if "people" in unit_text:
        if abs(value) >= 1_000_000_000:
            return f"{value / 1_000_000_000:,.2f}B"
        if abs(value) >= 1_000_000:
            return f"{value / 1_000_000:,.1f}M"
        return f"{value:,.0f}"
    if "dollar" in unit_text:
        if abs(value) >= 1_000_000_000_000:
            return f"${value / 1_000_000_000_000:,.2f}T"
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:,.1f}B"
        return f"${value:,.0f}"
    return f"{value:,.2f}"


def comparison_payload(
    indicator_code: str,
    country_codes: list[str],
    *,
    transform: str = "raw",
    start_year: int | None = None,
    end_year: int | None = None,
) -> dict[str, Any]:
    params: list[tuple[str, Any]] = [("indicator", indicator_code), ("transform", transform)]
    if start_year is not None:
        params.append(("start", f"{start_year}-01-01"))
    if end_year is not None:
        params.append(("end", f"{end_year}-12-31"))
    params.extend(("countries", code) for code in country_codes)
    try:
        return request("/v1/analytics/compare-countries", params)
    except httpx.HTTPStatusError as exc:
        detail = None
        try:
            payload = exc.response.json()
            detail = payload.get("detail") if isinstance(payload, dict) else None
        except ValueError:
            pass
        message = "The comparison could not be loaded."
        if detail:
            message = f"{message} {detail}"
        st.error(message)
        return {"transform": transform, "series": []}


def comparison_frame(payload: dict[str, Any]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for item in payload.get("series", []):
        frame = pd.DataFrame(item.get("points", []))
        if frame.empty:
            continue
        frame["date"] = pd.to_datetime(frame["date"])
        frame["year"] = frame["date"].dt.year
        frame["country_code"] = item.get("country_code")
        frame["Country"] = item.get("country_name")
        frame["units"] = item.get("units")
        frames.append(frame)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def latest_by_country(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    valid = frame.dropna(subset=["value"]).sort_values("date")
    if valid.empty:
        return valid
    return valid.groupby("country_code", as_index=False).tail(1).copy()


def series_points(series_id: str, transform: str = "raw") -> pd.DataFrame:
    payload = request(f"/v1/analytics/series/{series_id}", {"transform": transform})
    frame = pd.DataFrame(payload.get("points", []))
    if frame.empty:
        return frame
    frame["date"] = pd.to_datetime(frame["date"])
    frame["year"] = frame["date"].dt.year
    return frame


def latest_and_previous(frame: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None]:
    if frame.empty:
        return None, None
    valid = frame.dropna(subset=["value"]).sort_values("date")
    if valid.empty:
        return None, None
    latest = valid.iloc[-1]
    previous = valid.iloc[-2] if len(valid) > 1 else None
    return latest, previous


def data_age_label(timestamp: str | None) -> str:
    if not timestamp:
        return "Not yet refreshed"
    parsed = pd.to_datetime(timestamp, utc=True, errors="coerce")
    if pd.isna(parsed):
        return "Not available"
    return parsed.strftime("%Y-%m-%d")


try:
    health = request("/health")
    countries_payload = request("/v1/countries")
    indicators_payload = request("/v1/indicators")
except (httpx.HTTPError, ValueError) as exc:
    st.error("The dashboard cannot reach the data API. Check that the API service is running.")
    st.caption(str(exc))
    st.stop()

countries = countries_payload.get("items", [])
indicators = indicators_payload.get("items", [])

if not countries or not indicators:
    st.info("The database is ready, but no macroeconomic observations have been loaded yet.")
    st.code("docker compose exec api macro-data ingest", language="bash")
    st.stop()

country_by_name = {item["country_name"]: item for item in countries}
country_name_by_code = {item["country_code"]: item["country_name"] for item in countries}
country_codes = [item["country_code"] for item in countries]
comparable_indicators = [item for item in indicators if item["country_count"] >= 2]
indicator_by_name = {item["display_name"]: item for item in comparable_indicators}
indicator_by_code = {item["indicator_code"]: item for item in comparable_indicators}

summary_cols = st.columns(4)
summary_cols[0].metric("Economies", health.get("countries", 0))
summary_cols[1].metric("Indicators", len(comparable_indicators))
summary_cols[2].metric("Observations", f"{health.get('observations', 0):,}")
summary_cols[3].metric(
    "Data refreshed", data_age_label(health.get("latest_ingestion_completed_at"))
)

st.divider()
snapshot_tab, profile_tab, compare_tab, relationship_tab, catalog_tab = st.tabs(
    [
        "Global snapshot",
        "Country profile",
        "Compare economies",
        "Indicator relationships",
        "Data catalog",
    ]
)

with snapshot_tab:
    control_a, control_b = st.columns([1, 2])
    default_indicator_name = next(
        (
            item["display_name"]
            for item in comparable_indicators
            if item["indicator_code"] == "gdp_growth"
        ),
        comparable_indicators[0]["display_name"],
    )
    with control_a:
        selected_indicator_name = st.selectbox(
            "Indicator",
            list(indicator_by_name),
            index=list(indicator_by_name).index(default_indicator_name),
            key="snapshot_indicator",
        )
    with control_b:
        selected_country_names = st.multiselect(
            "Economies",
            list(country_by_name),
            default=list(country_by_name),
            max_selections=len(country_by_name),
            key="snapshot_countries",
        )

    selected_indicator = indicator_by_name[selected_indicator_name]
    selected_codes = [country_by_name[name]["country_code"] for name in selected_country_names]
    if selected_codes:
        snapshot = comparison_frame(
            comparison_payload(selected_indicator["indicator_code"], selected_codes)
        )
        latest = latest_by_country(snapshot)
        if latest.empty:
            st.info("No observations are available for this selection.")
        else:
            latest = latest.sort_values("value", ascending=True)
            highest = latest.iloc[-1]
            lowest = latest.iloc[0]
            median_value = float(latest["value"].median())

            stat_cols = st.columns(3)
            stat_cols[0].metric(
                "Highest reported",
                format_value(float(highest["value"]), selected_indicator.get("units")),
                help=f"{highest['Country']}, {int(highest['year'])}",
            )
            stat_cols[1].metric(
                "Median",
                format_value(median_value, selected_indicator.get("units")),
            )
            stat_cols[2].metric(
                "Lowest reported",
                format_value(float(lowest["value"]), selected_indicator.get("units")),
                help=f"{lowest['Country']}, {int(lowest['year'])}",
            )

            chart, table = st.columns([1.8, 1])
            with chart:
                fig = px.bar(
                    latest,
                    x="value",
                    y="Country",
                    orientation="h",
                    custom_data=["year"],
                    title=f"Latest available {selected_indicator_name.lower()}",
                )
                fig.update_traces(
                    hovertemplate=(
                        "%{y}<br>Value: %{x:,.2f}<br>Reported year: %{customdata[0]}<extra></extra>"
                    )
                )
                fig.update_layout(
                    xaxis_title=selected_indicator.get("units"),
                    yaxis_title=None,
                    margin=dict(l=10, r=10, t=55, b=10),
                )
                st.plotly_chart(fig, use_container_width=True)
            with table:
                ranking = latest.sort_values("value", ascending=False)[
                    ["Country", "value", "year"]
                ].copy()
                ranking.insert(0, "Rank", range(1, len(ranking) + 1))
                ranking = ranking.rename(columns={"value": "Value", "year": "Year"})
                st.dataframe(
                    ranking,
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Value": st.column_config.NumberColumn(format="%.2f")},
                )

            with st.expander("Historical context", expanded=False):
                trend_countries = st.multiselect(
                    "Show history for",
                    selected_country_names,
                    default=selected_country_names[:5],
                    max_selections=8,
                    key="snapshot_history_countries",
                )
                if trend_countries:
                    trend_codes = [
                        country_by_name[name]["country_code"] for name in trend_countries
                    ]
                    trend = comparison_frame(
                        comparison_payload(selected_indicator["indicator_code"], trend_codes)
                    )
                    if not trend.empty:
                        fig = px.line(
                            trend,
                            x="date",
                            y="value",
                            color="Country",
                            markers=True,
                        )
                        fig.update_layout(
                            xaxis_title=None,
                            yaxis_title=selected_indicator.get("units"),
                            legend_title=None,
                        )
                        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Values are compared using each economy's latest available observation. Reporting years can differ between countries."
    )

with profile_tab:
    selected_country_name = st.selectbox(
        "Economy",
        list(country_by_name),
        key="profile_country",
    )
    selected_country = country_by_name[selected_country_name]
    country_series = request(
        "/v1/series",
        {"country": selected_country["country_code"], "limit": 500},
    ).get("items", [])
    series_by_indicator = {
        item["indicator_code"]: item for item in country_series if item.get("indicator_code")
    }

    st.subheader(f"{selected_country_name} at a glance")
    core_indicators = [
        ("gdp_growth", "GDP growth"),
        ("inflation", "Inflation"),
        ("unemployment_rate", "Unemployment"),
        ("gdp_per_capita", "GDP per capita"),
    ]
    metric_columns = st.columns(4)
    for column, (code, label) in zip(metric_columns, core_indicators, strict=True):
        series = series_by_indicator.get(code)
        if series is None:
            column.metric(label, "—")
            continue
        frame = series_points(series["series_id"])
        latest, previous = latest_and_previous(frame)
        if latest is None:
            column.metric(label, "—")
            continue
        delta = None
        if previous is not None:
            delta = float(latest["value"]) - float(previous["value"])
        column.metric(
            f"{label} · {int(latest['year'])}",
            format_value(float(latest["value"]), series.get("units")),
            delta=(f"{delta:+,.2f} vs prior year" if delta is not None else None),
            delta_color="off",
        )

    st.subheader("Explore the history")
    available_series = sorted(country_series, key=lambda item: item["display_name"])
    labels = {item["display_name"]: item for item in available_series}
    selected_series_name = st.selectbox(
        "Indicator",
        list(labels),
        key="profile_indicator",
    )
    selected_series = labels[selected_series_name]
    transform_options = {
        "Reported value": "raw",
        "Change from previous year": "difference",
        "Percentage change from previous year": "pct_change",
        "Rolling z-score": "zscore",
    }
    selected_view = st.radio(
        "View",
        list(transform_options),
        horizontal=True,
        key="profile_transform",
    )
    profile_frame = series_points(selected_series["series_id"], transform_options[selected_view])

    if profile_frame.empty:
        st.info("No observations are available for this indicator.")
    else:
        y_title = (
            "Standard deviations"
            if selected_view == "Rolling z-score"
            else selected_series.get("units")
        )
        fig = px.line(
            profile_frame,
            x="date",
            y="value",
            markers=True,
            title=selected_series["display_name"],
        )
        fig.update_layout(xaxis_title=None, yaxis_title=y_title)
        st.plotly_chart(fig, use_container_width=True)

        raw_frame = series_points(selected_series["series_id"])
        export_frame = raw_frame[["year", "value"]].rename(
            columns={"year": "Year", "value": selected_series["display_name"]}
        )
        st.download_button(
            "Download this series",
            export_frame.to_csv(index=False).encode("utf-8"),
            file_name=(
                f"{selected_country['country_code'].lower()}_"
                f"{selected_series['indicator_code']}.csv"
            ),
            mime="text/csv",
        )

    with st.expander("Indicator definition"):
        st.write(selected_series.get("description") or "No description is available.")
        st.caption(
            f"World Bank indicator: {selected_series.get('provider_series_id')} · "
            f"Frequency: {selected_series.get('frequency') or 'Not specified'} · "
            f"Units: {selected_series.get('units') or 'Not specified'}"
        )

with compare_tab:
    filter_left, filter_right = st.columns([1, 2])
    with filter_left:
        compare_indicator_name = st.selectbox(
            "Indicator",
            list(indicator_by_name),
            key="compare_indicator",
        )
        compare_indicator = indicator_by_name[compare_indicator_name]
        comparison_views = {
            "Reported value": "raw",
            "Change from previous year": "difference",
            "Rolling z-score": "zscore",
        }
        comparison_view = st.selectbox(
            "View",
            list(comparison_views),
            key="compare_view",
        )
    with filter_right:
        compare_country_names = st.multiselect(
            "Economies",
            list(country_by_name),
            default=list(country_by_name)[:5],
            max_selections=10,
            key="compare_countries",
        )
        year_range = st.slider(
            "Period",
            min_value=1990,
            max_value=CURRENT_YEAR,
            value=(2000, CURRENT_YEAR),
            key="compare_period",
        )

    if compare_country_names:
        codes = [country_by_name[name]["country_code"] for name in compare_country_names]
        compare_frame = comparison_frame(
            comparison_payload(
                compare_indicator["indicator_code"],
                codes,
                transform=comparison_views[comparison_view],
                start_year=year_range[0],
                end_year=year_range[1],
            )
        )
        if compare_frame.empty:
            st.info("No observations are available for this comparison.")
        else:
            y_title = (
                "Standard deviations"
                if comparison_view == "Rolling z-score"
                else compare_indicator.get("units")
            )
            fig = px.line(
                compare_frame,
                x="date",
                y="value",
                color="Country",
                markers=True,
                title=compare_indicator_name,
            )
            fig.update_layout(xaxis_title=None, yaxis_title=y_title, legend_title=None)
            st.plotly_chart(fig, use_container_width=True)

            latest_compare = latest_by_country(compare_frame)
            if not latest_compare.empty:
                latest_compare = latest_compare.sort_values("value", ascending=False)
                latest_compare["Value"] = latest_compare["value"]
                latest_compare["Year"] = latest_compare["year"]
                st.dataframe(
                    latest_compare[["Country", "Value", "Year"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={"Value": st.column_config.NumberColumn(format="%.2f")},
                )

with relationship_tab:
    st.subheader("Explore relationships between indicators")
    relationship_cols = st.columns(3)
    indicator_names = list(indicator_by_name)
    default_x = next(
        (
            name
            for name, item in indicator_by_name.items()
            if item["indicator_code"] == "gdp_per_capita"
        ),
        indicator_names[0],
    )
    default_y = next(
        (name for name, item in indicator_by_name.items() if item["indicator_code"] == "inflation"),
        indicator_names[min(1, len(indicator_names) - 1)],
    )
    x_name = relationship_cols[0].selectbox(
        "Horizontal axis",
        indicator_names,
        index=indicator_names.index(default_x),
        key="relationship_x",
    )
    y_name = relationship_cols[1].selectbox(
        "Vertical axis",
        indicator_names,
        index=indicator_names.index(default_y),
        key="relationship_y",
    )
    selected_year = relationship_cols[2].slider(
        "Year",
        min_value=1990,
        max_value=CURRENT_YEAR,
        value=min(CURRENT_YEAR - 2, 2024),
        key="relationship_year",
    )

    x_indicator = indicator_by_name[x_name]
    y_indicator = indicator_by_name[y_name]
    x_frame = comparison_frame(comparison_payload(x_indicator["indicator_code"], country_codes))
    y_frame = comparison_frame(comparison_payload(y_indicator["indicator_code"], country_codes))

    if x_frame.empty or y_frame.empty:
        st.info("Not enough data is available for this relationship.")
    else:
        x_year = x_frame[x_frame["year"] == selected_year][
            ["country_code", "Country", "value"]
        ].rename(columns={"value": "x_value"})
        y_year = y_frame[y_frame["year"] == selected_year][["country_code", "value"]].rename(
            columns={"value": "y_value"}
        )
        relationship = x_year.merge(y_year, on="country_code", how="inner").dropna()

        if len(relationship) < 3:
            st.info(
                "Too few economies have both indicators for this year. Try an earlier year or another pair."
            )
        else:
            correlation = relationship["x_value"].corr(relationship["y_value"])
            st.metric(
                "Cross-country correlation",
                f"{correlation:.2f}",
                help="Pearson correlation across economies with both observations in the selected year.",
            )
            fig = px.scatter(
                relationship,
                x="x_value",
                y="y_value",
                text="Country",
                hover_name="Country",
                title=f"{x_name} and {y_name} · {selected_year}",
            )
            fig.update_traces(textposition="top center")
            fig.update_layout(
                xaxis_title=f"{x_name} ({x_indicator.get('units') or ''})".strip(),
                yaxis_title=f"{y_name} ({y_indicator.get('units') or ''})".strip(),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "This view is descriptive. A cross-country correlation does not imply a causal relationship."
            )

with catalog_tab:
    st.subheader("Data catalog")
    filter_cols = st.columns([2, 1, 1])
    search = filter_cols[0].text_input("Search indicators or countries")
    country_filter = filter_cols[1].selectbox(
        "Economy",
        ["All economies", *list(country_by_name)],
        key="catalog_country",
    )
    categories = sorted({item["category"] for item in indicators})
    category_filter = filter_cols[2].selectbox(
        "Category",
        ["All categories", *categories],
        key="catalog_category",
    )

    catalog_params: dict[str, Any] = {"limit": 500}
    if search:
        catalog_params["q"] = search
    if country_filter != "All economies":
        catalog_params["country"] = country_by_name[country_filter]["country_code"]
    if category_filter != "All categories":
        catalog_params["category"] = category_filter

    catalog = request("/v1/series", catalog_params)
    catalog_frame = pd.DataFrame(catalog.get("items", []))
    if catalog_frame.empty:
        st.info("No series match the selected filters.")
    else:
        display_columns = [
            "country_name",
            "display_name",
            "category",
            "frequency",
            "units",
            "provider_series_id",
            "observation_start",
            "observation_end",
        ]
        catalog_frame = catalog_frame[display_columns].rename(
            columns={
                "country_name": "Economy",
                "display_name": "Indicator",
                "category": "Category",
                "frequency": "Frequency",
                "units": "Units",
                "provider_series_id": "World Bank code",
                "observation_start": "Coverage starts",
                "observation_end": "Latest period",
            }
        )
        st.dataframe(catalog_frame, use_container_width=True, hide_index=True)
        st.download_button(
            "Download catalog",
            catalog_frame.to_csv(index=False).encode("utf-8"),
            file_name="macroeconomic_data_catalog.csv",
            mime="text/csv",
        )

st.divider()
st.caption(
    "Source: World Bank Indicators API. The platform keeps provider identifiers and revision history for traceability."
)
