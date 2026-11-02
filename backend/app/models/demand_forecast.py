from sqlalchemy import CheckConstraint, Column, Date, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database.session import Base


class DemandForecast(Base):
    __tablename__ = "demand_forecasts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    forecast_quantity = Column(Integer, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "forecast_quantity >= 0",
            name="check_demand_forecast_quantity_non_negative",
        ),
        CheckConstraint(
            "period_end >= period_start",
            name="check_demand_forecast_period_valid",
        ),
    )

    # Relationships
    product = relationship("Product", back_populates="demand_forecasts")

    def __repr__(self) -> str:
        return (
            f"<DemandForecast(id={self.id}, product_id={self.product_id}, "
            f"forecast={self.forecast_quantity}, start={self.period_start}, end={self.period_end})>"
        )

