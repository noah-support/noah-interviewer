from peewee import AutoField, CharField, DateTimeField, ForeignKeyField, Model, SQL, TextField

from database import db


class BaseModel(Model):
    class Meta:
        database = db


class Project(BaseModel):
    id = AutoField()
    title = CharField(max_length=100)

    # Internal fields (not shown/edited in the prototype UI yet).
    graph = CharField()
    namespace = CharField()

    created_at = DateTimeField(constraints=[SQL("DEFAULT NOW()")])

    class Meta:
        table_name = "projects"


class Interview(BaseModel):
    STATUS_READY = "Ready"
    STATUS_PAUSED = "paused"
    STATUS_FAILED = "failed"
    STATUS_DONE = "done"
    STATUS_VALUES = (STATUS_READY, STATUS_PAUSED, STATUS_FAILED, STATUS_DONE)

    id = AutoField()
    project = ForeignKeyField(Project, backref="interviews", on_delete="CASCADE")

    username = CharField(max_length=20)
    code = CharField(max_length=6)

    content = TextField()
    summary = TextField()

    status = CharField(
        max_length=10,
        constraints=[
            # Basic DB-level validation so bad status values don't silently land.
            SQL(
                "CHECK (status IN ('Ready','paused','failed','done'))"
            )
        ],
    )

    created_at = DateTimeField(constraints=[SQL("DEFAULT NOW()")])

    class Meta:
        table_name = "interviews"