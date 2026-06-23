"""Tests for Alembic migration infrastructure.

Runs migrations against an in-memory SQLite database to verify:
- upgrade to head works
- downgrade to base works
- round-trip (up → down → up) works
- schema matches expected columns and foreign keys
"""

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ALEMBIC_INI = "alembic.ini"


@pytest.fixture()
def alembic_engine():
    return create_engine("sqlite://")


@pytest.fixture()
def alembic_cfg(alembic_engine):
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", "sqlite://")
    cfg.attributes["connection"] = alembic_engine.connect()
    return cfg


def test_upgrade_head(alembic_cfg, alembic_engine):
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(alembic_engine)
    tables = inspector.get_table_names()
    assert "template" in tables
    assert "formsubmission" in tables
    assert "alembic_version" in tables


def test_downgrade_base(alembic_cfg, alembic_engine):
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")

    inspector = inspect(alembic_engine)
    tables = inspector.get_table_names()
    assert "template" not in tables
    assert "formsubmission" not in tables


def test_round_trip(alembic_cfg, alembic_engine):
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "-1")
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(alembic_engine)
    tables = inspector.get_table_names()
    assert "template" in tables
    assert "formsubmission" in tables


def test_template_columns(alembic_cfg, alembic_engine):
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(alembic_engine)
    columns = {c["name"] for c in inspector.get_columns("template")}
    assert columns == {"id", "name", "fields", "pdf_path", "created_at"}


def test_formsubmission_columns(alembic_cfg, alembic_engine):
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(alembic_engine)
    columns = {c["name"] for c in inspector.get_columns("formsubmission")}
    assert columns == {"id", "template_id", "input_text", "output_pdf_path", "created_at"}


def test_formsubmission_fk(alembic_cfg, alembic_engine):
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(alembic_engine)
    fks = inspector.get_foreign_keys("formsubmission")
    assert len(fks) == 1
    assert fks[0]["referred_table"] == "template"
    assert fks[0]["referred_columns"] == ["id"]
