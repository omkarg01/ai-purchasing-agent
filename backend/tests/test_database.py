from sqlalchemy import inspect
from app.database.session import Base, init_db, get_db, create_engine


def test_init_db_creates_all_tables(engine):
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    expected_tables = {
        "products",
        "inventories",
        "demand_forecasts",
        "suppliers",
        "supplier_products",
        "purchase_recommendations",
        "purchase_orders",
        "purchasing_budgets",
    }

    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"


def test_get_db_generator():
    db_gen = get_db()
    session = next(db_gen)
    assert session is not None
    # Ensure closing the generator cleans up without error
    try:
        next(db_gen)
    except StopIteration:
        pass

