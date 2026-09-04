"""The Snapshot: an append-only SQLite log of Observations plus a Run journal (ADR 5).

Phase 1 keys rows by the profile *slug* — the ``profile`` and ``watchlist_entry``
tables arrive in Phase 2 when the UI takes ownership of configuration (ADR 10).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from .migrations import migrate
from .models import Availability, MatchReason, Observation


class Base(DeclarativeBase):
    pass


class RunRow(Base):
    __tablename__ = "run"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_slug: Mapped[str] = mapped_column(String, index=True)
    trigger: Mapped[str] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")
    delta_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(String, nullable=True)


class ObservationRow(Base):
    __tablename__ = "observation"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(Integer, index=True)
    profile_slug: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    source_item_id: Mapped[str] = mapped_column(String, index=True)
    match_reason: Mapped[str] = mapped_column(String)
    watchlist_key: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    availability: Mapped[str | None] = mapped_column(String, nullable=True)
    reservation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_from: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    blurb: Mapped[str | None] = mapped_column(String, nullable=True)
    subtitle: Mapped[str | None] = mapped_column(String, nullable=True)
    series: Mapped[str | None] = mapped_column(String, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, index=True)

    # Serves the max-id-per-item lookup that every diff starts with.
    __table_args__ = (
        Index("ix_observation_item", "profile_slug", "source", "source_item_id", "id"),
    )


class ResolutionRow(Base):
    """What a Source decided a Watchlist Entry refers to.

    Derived state, so it lives here rather than being written back into the
    user's ``watchlist.yaml`` — that file stays hand-owned, comments and all.
    Negative outcomes are cached too, so a title the library does not have is
    not re-searched on every Run.
    """

    __tablename__ = "resolution"

    id: Mapped[int] = mapped_column(primary_key=True)
    profile_slug: Mapped[str] = mapped_column(String, index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    watchlist_key: Mapped[str] = mapped_column(String, index=True)
    url: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String, default="")
    matched_title: Mapped[str | None] = mapped_column(String, nullable=True)
    matched_author: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint("profile_slug", "source", "watchlist_key", name="uq_resolution_entry"),
    )


class SeededScopeRow(Base):
    """A discovery scope we have already looked at once.

    Derived from the Observations in principle, but deriving it meant a DISTINCT
    over the whole history on every Run — 1.3 seconds after three years, and
    growing. There is only ever a handful of scopes, so they are recorded as
    they are seen instead: constant cost, no scan.
    """

    __tablename__ = "seeded_scope"

    profile_slug: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, primary_key=True)
    match_reason: Mapped[str] = mapped_column(String, primary_key=True)
    #: Empty string rather than NULL — it is part of the primary key.
    category: Mapped[str] = mapped_column(String, primary_key=True, default="")


class StateRow(Base):
    """Small bits of bookkeeping that belong to no other table."""

    __tablename__ = "state"

    profile_slug: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[datetime] = mapped_column(DateTime)


def _to_observation(row: ObservationRow) -> Observation:
    return Observation(
        source=row.source,
        source_item_id=row.source_item_id,
        title=row.title,
        match_reason=MatchReason(row.match_reason),
        blurb=row.blurb,
        subtitle=row.subtitle,
        series=row.series,
        author=row.author,
        watchlist_key=row.watchlist_key,
        price_cents=row.price_cents,
        original_price_cents=row.original_price_cents,
        availability=Availability(row.availability) if row.availability else None,
        reservation_count=row.reservation_count,
        available_from=row.available_from,
        category=row.category,
        url=row.url,
        observed_at=row.observed_at,
    )


class Store:
    """Owns the SQLite file. Schema is created on first use."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{path}")
        migrate(self._engine, Base.metadata)

    def session(self) -> Session:
        return Session(self._engine)

    def start_run(self, profile_slug: str, trigger: str, started_at: datetime) -> int:
        with self.session() as session:
            run = RunRow(
                profile_slug=profile_slug,
                trigger=trigger,
                started_at=started_at,
                status="running",
            )
            session.add(run)
            session.commit()
            return run.id

    def finish_run(
        self,
        run_id: int,
        *,
        status: str,
        delta_count: int,
        finished_at: datetime,
        error: str | None = None,
    ) -> None:
        with self.session() as session:
            run = session.get(RunRow, run_id)
            if run is None:  # pragma: no cover - only reachable if the row was deleted
                raise LookupError(f"run {run_id} vanished")
            run.status = status
            run.delta_count = delta_count
            run.finished_at = finished_at
            run.error = error
            session.commit()

    def last_finished_run(self, profile_slug: str, before_run_id: int) -> RunRow | None:
        """The previous completed Run — what the Digest means by 'last check'."""
        with self.session() as session:
            stmt = (
                select(RunRow)
                .where(
                    RunRow.profile_slug == profile_slug,
                    RunRow.id < before_run_id,
                    RunRow.finished_at.is_not(None),
                )
                .order_by(RunRow.id.desc())
                .limit(1)
            )
            row = session.scalars(stmt).first()
            if row is not None:
                session.expunge(row)
            return row

    def latest_observations(
        self, profile_slug: str, keys: Iterable[tuple[str, str]]
    ) -> dict[tuple[str, str], Observation]:
        """The most recent stored Observation for each ``(source, source_item_id)``.

        Resolved with a max-id-per-item subquery so the cost tracks the number of
        watched items, not the length of the append-only history.
        """
        wanted = set(keys)
        if not wanted:
            return {}
        sources = {source for source, _ in wanted}
        item_ids = {item_id for _, item_id in wanted}

        latest_ids = (
            select(func.max(ObservationRow.id))
            .where(
                ObservationRow.profile_slug == profile_slug,
                ObservationRow.source.in_(sources),
                ObservationRow.source_item_id.in_(item_ids),
            )
            .group_by(ObservationRow.source, ObservationRow.source_item_id)
        )

        found: dict[tuple[str, str], Observation] = {}
        with self.session() as session:
            stmt = select(ObservationRow).where(ObservationRow.id.in_(latest_ids))
            for row in session.scalars(stmt):
                key = (row.source, row.source_item_id)
                # in_() pairs the sets independently, so a cross-source id
                # collision can come back; keep only the pairs we asked for.
                if key in wanted:
                    found[key] = _to_observation(row)
        return found

    def get_resolution(
        self, profile_slug: str, source: str, watchlist_key: str
    ) -> ResolutionRow | None:
        with self.session() as session:
            stmt = select(ResolutionRow).where(
                ResolutionRow.profile_slug == profile_slug,
                ResolutionRow.source == source,
                ResolutionRow.watchlist_key == watchlist_key,
            )
            row = session.scalars(stmt).first()
            if row is not None:
                session.expunge(row)
            return row

    def put_resolution(
        self,
        profile_slug: str,
        source: str,
        watchlist_key: str,
        *,
        url: str | None,
        confidence: str,
        reason: str,
        matched_title: str | None,
        matched_author: str | None,
        resolved_at: datetime,
    ) -> None:
        with self.session() as session:
            stmt = select(ResolutionRow).where(
                ResolutionRow.profile_slug == profile_slug,
                ResolutionRow.source == source,
                ResolutionRow.watchlist_key == watchlist_key,
            )
            row = session.scalars(stmt).first()
            if row is None:
                row = ResolutionRow(
                    profile_slug=profile_slug, source=source, watchlist_key=watchlist_key
                )
                session.add(row)
            row.url = url
            row.confidence = confidence
            row.reason = reason
            row.matched_title = matched_title
            row.matched_author = matched_author
            row.resolved_at = resolved_at
            session.commit()

    def get_state(self, profile_slug: str, key: str) -> datetime | None:
        with self.session() as session:
            row = session.get(StateRow, (profile_slug, key))
            return row.value if row is not None else None

    def set_state(self, profile_slug: str, key: str, value: datetime) -> None:
        with self.session() as session:
            row = session.get(StateRow, (profile_slug, key))
            if row is None:
                row = StateRow(profile_slug=profile_slug, key=key)
                session.add(row)
            row.value = value
            session.commit()

    def seeded_scopes(self, profile_slug: str) -> set[tuple[str, str, str]]:
        """Which ``(source, match_reason, category)`` scopes we have already seen.

        Asked *before* this Run's Observations are appended, so a shelf being
        followed for the first time is recognisable as such.
        """
        with self.session() as session:
            stmt = select(
                SeededScopeRow.source,
                SeededScopeRow.match_reason,
                SeededScopeRow.category,
            ).where(SeededScopeRow.profile_slug == profile_slug)
            return {tuple(row) for row in session.execute(stmt)}  # type: ignore[misc]

    def mark_seeded(self, profile_slug: str, scopes: Iterable[tuple[str, str, str]]) -> None:
        with self.session() as session:
            known = {
                tuple(row)
                for row in session.execute(
                    select(
                        SeededScopeRow.source,
                        SeededScopeRow.match_reason,
                        SeededScopeRow.category,
                    ).where(SeededScopeRow.profile_slug == profile_slug)
                )
            }
            for scope in scopes:
                if scope in known:
                    continue
                source, reason, category = scope
                session.add(
                    SeededScopeRow(
                        profile_slug=profile_slug,
                        source=source,
                        match_reason=reason,
                        category=category,
                    )
                )
                known.add(scope)
            session.commit()

    def append(
        self,
        run_id: int,
        profile_slug: str,
        observations: Sequence[Observation],
        observed_at: datetime,
    ) -> None:
        if not observations:
            return
        with self.session() as session:
            session.add_all(
                ObservationRow(
                    run_id=run_id,
                    profile_slug=profile_slug,
                    source=obs.source,
                    source_item_id=obs.source_item_id,
                    match_reason=str(obs.match_reason),
                    watchlist_key=obs.watchlist_key,
                    title=obs.title,
                    author=obs.author,
                    price_cents=obs.price_cents,
                    original_price_cents=obs.original_price_cents,
                    availability=str(obs.availability) if obs.availability else None,
                    reservation_count=obs.reservation_count,
                    available_from=obs.available_from,
                    category=obs.category,
                    url=obs.url,
                    blurb=obs.blurb,
                    subtitle=obs.subtitle,
                    series=obs.series,
                    observed_at=obs.observed_at or observed_at,
                )
                for obs in observations
            )
            session.commit()
