from database import db
from models import Interview, Project, ProjectDocument

import os

from pinecone import Pinecone  # type: ignore[import-not-found]


def clean_database() -> None:
    """Delete all rows so the schema starts from a known empty state."""
    db.connect(reuse_if_open=True)
    try:
        # Best-effort: purge pinecone namespaces for existing projects.
        try:
            for p in Project.select():
                ns = (p.namespace or "").strip() or f"project-{p.id}"
                try:
                    api_key = os.getenv("PINECONE_API_KEY")
                    if api_key:
                        index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
                        pc = Pinecone(api_key=api_key)
                        index = pc.Index(index_name)
                        index.delete(namespace=ns, delete_all=True)
                except Exception as e:
                    print(f"[SYSTEM] failed to delete pinecone namespace {ns!r}: {e}")
        except Exception:
            # If tables don't exist yet, ignore.
            pass

        # Delete in child->parent order for FK integrity.
        ProjectDocument.delete().execute()
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
        project.namespace = f"project-{project.id}"
        project.save()
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if api_key:
                index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
                pc = Pinecone(api_key=api_key)
                index = pc.Index(index_name)
                index.upsert(
                    namespace=project.namespace,
                    vectors=[
                        {
                            "id": "__namespace_init__",
                            "values": [0.0] * 1024,
                            "metadata": {
                                "doc_id": 0,
                                "chunk_id": 0,
                                "source_filename": "__namespace__",
                                "text": "",
                            },
                        }
                    ],
                )
        except Exception as e:
            print(f"[SYSTEM] failed to touch pinecone namespace: {e}")
        Interview.create(
            project=project,
            username="user",
            code="ABC123",
            status="Ready",
            content="",
            summary="",
            discovery_state_json="",
        )
    finally:
        db.close()


def ensure_seeded_if_empty() -> None:
    """
    Ensure tables exist and insert the demo project/interview when there are no interviews.

    Used on API startup so the DB is repopulated after e.g. `interviewer.py` exits with
    `clean_database()`, without requiring `python main.py` (which skips seed when using
    `uvicorn main:app`).
    """
    db.connect(reuse_if_open=True)
    try:
        db.create_tables([Project, Interview, ProjectDocument], safe=True)
        if Interview.select().count() > 0:
            return
        seed_database()
    finally:
        db.close()


def reset_and_seed() -> None:
    """Ensure tables exist, clean rows, then seed the initial data."""
    db.connect(reuse_if_open=True)
    try:
        # Best-effort: purge pinecone namespaces for existing projects before dropping tables.
        try:
            for p in Project.select():
                ns = (p.namespace or "").strip() or f"project-{p.id}"
                try:
                    api_key = os.getenv("PINECONE_API_KEY")
                    if api_key:
                        index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
                        pc = Pinecone(api_key=api_key)
                        index = pc.Index(index_name)
                        index.delete(namespace=ns, delete_all=True)
                except Exception as e:
                    print(f"[SYSTEM] failed to delete pinecone namespace {ns!r}: {e}")
        except Exception:
            pass

        # Recreate tables to apply schema changes (e.g. adding FKs).
        db.drop_tables([ProjectDocument, Interview, Project], safe=True)
        db.create_tables([Project, Interview, ProjectDocument])

        ProjectDocument.delete().execute()
        Interview.delete().execute()
        Project.delete().execute()

        project = Project.create(
            title="Default Project",
            graph="",
            namespace="",
        )
        project.namespace = f"project-{project.id}"
        project.save()
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            if api_key:
                index_name = os.getenv("PINECONE_INDEX_NAME", "interviewer-docs")
                pc = Pinecone(api_key=api_key)
                index = pc.Index(index_name)
                index.upsert(
                    namespace=project.namespace,
                    vectors=[
                        {
                            "id": "__namespace_init__",
                            "values": [0.0] * 1024,
                            "metadata": {
                                "doc_id": 0,
                                "chunk_id": 0,
                                "source_filename": "__namespace__",
                                "text": "",
                            },
                        }
                    ],
                )
        except Exception as e:
            print(f"[SYSTEM] failed to touch pinecone namespace: {e}")

        Interview.create(
            project=project,
            username="user",
            code="ABC123",
            status="Ready",
            content="",
            summary="",
            discovery_state_json="",
        )
    finally:
        db.close()

