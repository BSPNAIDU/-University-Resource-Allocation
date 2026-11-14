"""Add exam sessions and link registrations and allocations."""

from alembic import op
import sqlalchemy as sa

revision = "d4e8b71c92af"
down_revision = "c83d51a7e902"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "exam_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("university_id", sa.Integer(), sa.ForeignKey("universities.id"), nullable=False),
        sa.Column("examination_id", sa.Integer(), sa.ForeignKey("examinations.id"), nullable=False),
        sa.Column("session_name", sa.String(50), nullable=False),
        sa.Column("exam_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="300"),
        sa.UniqueConstraint("examination_id", "session_name", name="uq_examination_session_name"),
    )

    op.create_index("ix_exam_sessions_university_id", "exam_sessions", ["university_id"])
    op.create_index("ix_exam_sessions_examination_id", "exam_sessions", ["examination_id"])

    op.add_column("exam_registrations", sa.Column("session_id", sa.Integer(), nullable=True))
    op.add_column("allocations", sa.Column("session_id", sa.Integer(), nullable=True))

    op.execute("""
        INSERT INTO exam_sessions
            (university_id, examination_id, session_name,
             exam_date, start_time, duration_minutes, capacity)
        SELECT university_id, id, 'Existing',
               exam_date, start_time, duration_minutes,
               GREATEST(student_count, 300)
        FROM examinations
    """)

    op.execute("""
        UPDATE exam_registrations AS r
        SET session_id = s.id
        FROM exam_sessions AS s
        WHERE s.examination_id = r.examination_id
    """)

    op.execute("""
        UPDATE allocations AS a
        SET session_id = s.id
        FROM exam_sessions AS s
        WHERE s.examination_id = a.examination_id
    """)

    op.alter_column("exam_registrations", "session_id", nullable=False)
    op.alter_column("allocations", "session_id", nullable=False)

    op.create_foreign_key(
        "fk_exam_registrations_session_id",
        "exam_registrations", "exam_sessions",
        ["session_id"], ["id"]
    )

    op.create_foreign_key(
        "fk_allocations_session_id",
        "allocations", "exam_sessions",
        ["session_id"], ["id"]
    )

    op.create_index("ix_exam_registrations_session_id", "exam_registrations", ["session_id"])
    op.create_index("ix_allocations_session_id", "allocations", ["session_id"])

    op.drop_constraint("uq_exam_room_seat", "allocations", type_="unique")
    op.create_unique_constraint(
        "uq_session_room_seat",
        "allocations",
        ["session_id", "resource_id", "seat_number"]
    )


def downgrade():
    raise RuntimeError("Session migration cannot be safely downgraded.")
