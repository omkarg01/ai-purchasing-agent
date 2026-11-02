from sqlalchemy import CheckConstraint, Column, Integer, Numeric

from app.database.session import Base


class PurchasingBudget(Base):
    __tablename__ = "purchasing_budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    total_budget = Column(Numeric(12, 2), nullable=False)
    committed_amount = Column(Numeric(12, 2), nullable=False, default=0.0)

    __table_args__ = (
        CheckConstraint(
            "total_budget >= 0",
            name="check_budget_total_non_negative",
        ),
        CheckConstraint(
            "committed_amount >= 0",
            name="check_budget_committed_non_negative",
        ),
    )

    @property
    def remaining_budget(self) -> float:
        """Returns the uncommitted remaining budget."""
        return float(self.total_budget - (self.committed_amount or 0))

    def __repr__(self) -> str:
        return (
            f"<PurchasingBudget(id={self.id}, total={self.total_budget}, "
            f"committed={self.committed_amount})>"
        )

