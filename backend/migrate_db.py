from sqlalchemy import inspect, text

from database import engine


NEW_COLUMNS = {
    "service_name": "VARCHAR DEFAULT 'victim-app'",
    "root_cause": "TEXT",
    "confidence": "FLOAT",
    "evidence": "TEXT",
    "recommended_action": "TEXT",
    "risk": "VARCHAR",
}


def migrate():
    inspector = inspect(engine)

    if "incidents" not in inspector.get_table_names():
        print("incidents table does not exist yet.")
        print("Run the backend once so SQLAlchemy creates it, then rerun this migration.")
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("incidents")
    }

    with engine.begin() as connection:
        for column_name, column_definition in NEW_COLUMNS.items():
            if column_name in existing_columns:
                print(f"[skip] {column_name} already exists")
                continue

            sql = text(
                f"ALTER TABLE incidents ADD COLUMN "
                f"{column_name} {column_definition}"
            )

            connection.execute(sql)
            print(f"[added] {column_name}")


if __name__ == "__main__":
    migrate()
