"""Monotonic RuleBundle generation — independent of per-row restriction versions."""

from sqlmodel import Session

from app.models.rule_bundle_meta import SINGLETON_ID, RuleBundleMeta


def get_bundle_version(session: Session) -> int:
    row = session.get(RuleBundleMeta, SINGLETON_ID)
    return int(row.version) if row is not None else 0


def bump_bundle_version(session: Session) -> int:
    row = session.get(RuleBundleMeta, SINGLETON_ID)
    if row is None:
        row = RuleBundleMeta(id=SINGLETON_ID, version=0)
        session.add(row)
        session.flush()
    row.version += 1
    session.add(row)
    session.flush()
    return int(row.version)
