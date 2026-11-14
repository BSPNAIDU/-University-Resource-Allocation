"""Add multi-university support

Revision ID: b72c91d4e605
Revises: 9182a4076806
"""
from alembic import op
import sqlalchemy as sa

revision = "b72c91d4e605"
down_revision = "9182a4076806"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Create universities table
    op.create_table(
        "universities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("university_name", sa.String(200), nullable=False),
        sa.Column("university_code", sa.String(50), nullable=False),
        sa.Column("address", sa.String(300), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_universities_university_name", "universities", ["university_name"], unique=True)
    op.create_index("ix_universities_university_code", "universities", ["university_code"], unique=True)

    # 2. Add nullable university_id columns first
    for table in ["students", "resources", "examinations", "exam_registrations", "allocations"]:
        op.add_column(table, sa.Column("university_id", sa.Integer(), nullable=True))

    # 3. Preserve existing data under a temporary legacy university
    op.execute("""
        INSERT INTO universities (university_name, university_code, is_active)
        VALUES ('Legacy University', 'LEGACY001', TRUE)
    """)
    op.execute("""
        UPDATE students SET university_id =
        (SELECT id FROM universities WHERE university_code = 'LEGACY001')
    """)
    op.execute("""
        UPDATE resources SET university_id =
        (SELECT id FROM universities WHERE university_code = 'LEGACY001')
    """)
    op.execute("""
        UPDATE examinations SET university_id =
        (SELECT id FROM universities WHERE university_code = 'LEGACY001')
    """)
    op.execute("""
        UPDATE exam_registrations SET university_id =
        (SELECT id FROM universities WHERE university_code = 'LEGACY001')
    """)
    op.execute("""
        UPDATE allocations SET university_id =
        (SELECT id FROM universities WHERE university_code = 'LEGACY001')
    """)

    # 4. Make university_id mandatory and add foreign keys
    for table in ["students", "resources", "examinations", "exam_registrations", "allocations"]:
        op.alter_column(table, "university_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table}_university_id",
            table,
            "universities",
            ["university_id"],
            ["id"],
        )
        op.create_index(f"ix_{table}_university_id", table, ["university_id"])

    # 5. Replace globally unique identifiers with university-scoped uniqueness
    op.execute("""
        DROP INDEX IF EXISTS ix_students_student_number;
        DROP INDEX IF EXISTS ix_resources_room_number;
        DROP INDEX IF EXISTS ix_examinations_exam_code;
    """)

    op.create_unique_constraint(
        "uq_university_student_number",
        "students",
        ["university_id", "student_number"],
    )
    op.create_unique_constraint(
        "uq_university_building_room",
        "resources",
        ["university_id", "building", "room_number"],
    )
    op.create_unique_constraint(
        "uq_university_exam_code",
        "examinations",
        ["university_id", "exam_code"],
    )


def downgrade():
    for table in ["students", "resources", "examinations", "exam_registrations", "allocations"]:
        op.drop_index(f"ix_{table}_university_id", table_name=table)
        op.drop_constraint(f"fk_{table}_university_id", table, type_="foreignkey")
        op.drop_column(table, "university_id")

    op.drop_constraint("uq_university_student_number", "students", type_="unique")
    op.drop_constraint("uq_university_building_room", "resources", type_="unique")
    op.drop_constraint("uq_university_exam_code", "examinations", type_="unique")

    op.create_index("ix_students_student_number", "students", ["student_number"], unique=True)
    op.create_index("ix_resources_room_number", "resources", ["room_number"], unique=True)
    op.create_index("ix_examinations_exam_code", "examinations", ["exam_code"], unique=True)

    op.drop_index("ix_universities_university_name", table_name="universities")
    op.drop_index("ix_universities_university_code", table_name="universities")
    op.drop_table("universities")
