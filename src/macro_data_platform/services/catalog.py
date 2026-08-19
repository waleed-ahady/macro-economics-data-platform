from collections import defaultdict
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from macro_data_platform.models import EconomicSeries, Observation


def list_series(
    session: Session,
    *,
    query: str | None = None,
    category: str | None = None,
    source: str | None = None,
    country_code: str | None = None,
    indicator_code: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[int, list[EconomicSeries]]:
    conditions = [EconomicSeries.enabled.is_(True)]
    if query:
        pattern = f"%{query}%"
        conditions.append(
            or_(
                EconomicSeries.series_id.ilike(pattern),
                EconomicSeries.provider_series_id.ilike(pattern),
                EconomicSeries.indicator_code.ilike(pattern),
                EconomicSeries.display_name.ilike(pattern),
                EconomicSeries.title.ilike(pattern),
                EconomicSeries.country_name.ilike(pattern),
            )
        )
    if category:
        conditions.append(EconomicSeries.category == category)
    if source:
        conditions.append(EconomicSeries.source == source.upper())
    if country_code:
        conditions.append(EconomicSeries.country_code == country_code.upper())
    if indicator_code:
        conditions.append(EconomicSeries.indicator_code == indicator_code)

    total = session.scalar(select(func.count()).select_from(EconomicSeries).where(*conditions)) or 0
    items = list(
        session.scalars(
            select(EconomicSeries)
            .where(*conditions)
            .order_by(
                EconomicSeries.country_name,
                EconomicSeries.category,
                EconomicSeries.display_name,
                EconomicSeries.source,
            )
            .limit(limit)
            .offset(offset)
        )
    )
    return total, items


def get_series(session: Session, series_id: str) -> EconomicSeries | None:
    return session.get(EconomicSeries, series_id)


def get_observations(
    session: Session,
    series_id: str,
    *,
    start: date | None = None,
    end: date | None = None,
    limit: int = 5000,
    ascending: bool = True,
) -> list[Observation]:
    statement = select(Observation).where(Observation.series_id == series_id)
    if start:
        statement = statement.where(Observation.observation_date >= start)
    if end:
        statement = statement.where(Observation.observation_date <= end)
    order = Observation.observation_date.asc() if ascending else Observation.observation_date.desc()
    return list(session.scalars(statement.order_by(order).limit(limit)))


def get_latest_observation(session: Session, series_id: str) -> Observation | None:
    return session.scalar(
        select(Observation)
        .where(Observation.series_id == series_id)
        .order_by(Observation.observation_date.desc())
        .limit(1)
    )


def find_country_indicator_series(
    session: Session,
    country_code: str,
    indicator_code: str,
    *,
    source: str = "WORLD_BANK",
) -> EconomicSeries | None:
    return session.scalar(
        select(EconomicSeries)
        .where(
            EconomicSeries.enabled.is_(True),
            EconomicSeries.country_code == country_code.upper(),
            EconomicSeries.indicator_code == indicator_code,
            EconomicSeries.source == source.upper(),
        )
        .limit(1)
    )


def country_catalog(session: Session) -> list[dict[str, object]]:
    rows = session.execute(
        select(
            EconomicSeries.country_code,
            EconomicSeries.country_name,
            func.count(EconomicSeries.series_id),
            func.count(func.distinct(EconomicSeries.indicator_code)),
        )
        .where(
            EconomicSeries.enabled.is_(True),
            EconomicSeries.country_code.is_not(None),
        )
        .group_by(EconomicSeries.country_code, EconomicSeries.country_name)
        .order_by(EconomicSeries.country_name)
    ).all()
    return [
        {
            "country_code": country_code,
            "country_name": country_name,
            "series_count": series_count,
            "indicator_count": indicator_count,
        }
        for country_code, country_name, series_count, indicator_count in rows
    ]


def indicator_catalog(session: Session) -> list[dict[str, object]]:
    rows = session.execute(
        select(EconomicSeries).where(
            EconomicSeries.enabled.is_(True),
            EconomicSeries.indicator_code.is_not(None),
        )
    ).scalars()

    grouped: dict[str, dict[str, object]] = {}
    countries: dict[str, set[str]] = defaultdict(set)
    sources: dict[str, set[str]] = defaultdict(set)
    for series in rows:
        code = series.indicator_code
        if code is None:
            continue
        if code not in grouped:
            grouped[code] = {
                "indicator_code": code,
                "display_name": series.display_name,
                "category": series.category,
                "units": series.units,
            }
        if series.country_code:
            countries[code].add(series.country_code)
        sources[code].add(series.source)

    output = []
    for code, item in grouped.items():
        output.append(
            {
                **item,
                "country_count": len(countries[code]),
                "sources": sorted(sources[code]),
            }
        )
    return sorted(output, key=lambda item: (str(item["category"]), str(item["display_name"])))
