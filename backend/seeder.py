from database import db
from models import Project, Interview


def clean_database() -> None:
    """Delete all rows so the schema starts from a known empty state."""
    db.connect(reuse_if_open=True)
    try:
        # Delete in child->parent order for FK integrity.
        Interview.delete().execute()
        Project.delete().execute()
    finally:
        db.close()


def seed_database() -> None:
    """Seed one project + one interview (with empty content/summary)."""
    db.connect(reuse_if_open=True)
    try:
        project = Project.create(
            title="Default Project",
            graph="",
            namespace="",
        )

        Interview.create(
            project=project,
            username="user",
            code="demo",
            status="Ready",
            content="",
            summary="",
        )
    finally:
        db.close()


def reset_and_seed() -> None:
    """Ensure tables exist, clean rows, then seed the initial data."""
    db.connect(reuse_if_open=True)
    try:
        # Recreate tables to apply schema changes (e.g. adding FKs).
        db.drop_tables([Interview, Project], safe=True)
        db.create_tables([Project, Interview])

        Interview.delete().execute()
        Project.delete().execute()

        project = Project.create(
            title="Default Project",
            graph="",
            namespace="",
        )

        Interview.create(
            project=project,
            username="user",
            code="demo",
            status="Ready",
            content="",
            summary="",
        )
    finally:
        db.close()

