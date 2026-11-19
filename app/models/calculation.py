# app/models/calculation.py
"""
Calculation model with single-table polymorphic inheritance and a factory.

Design decisions:
- One table ("calculations") holds every calculation type.
- The `type` column is the discriminator; SQLAlchemy returns the right
  subclass (Addition, Subtraction, ...) when loading rows.
- `a` and `b` are the two operands.
- `result` is STORED when a calculation is created through the factory,
  and get_result() can always recompute it on demand.
- `user_id` is a foreign key to users.id (deleted with the user).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.user import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Calculation(Base):
    """
    Base calculation model.

    Subclasses only override get_result() and set a polymorphic identity;
    they share this table, so they don't define __tablename__.
    """

    __tablename__ = "calculations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    a = Column(Float, nullable=False)
    b = Column(Float, nullable=False)
    type = Column(String(50), nullable=False, index=True)
    result = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    # Requires User to define: calculations = relationship("Calculation", back_populates="user")
    user = relationship("User", back_populates="calculations")

    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "calculation",
    }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def create(cls, calculation_type: str, user_id: uuid.UUID,
               a: float, b: float) -> "Calculation":
        """
        Factory: return the correct subclass for `calculation_type`.

        Accepts (case-insensitive): addition/add, subtraction/sub/subtract,
        multiplication/multiply, division/divide.

        The result is computed and stored immediately, so invalid input
        (e.g. dividing by zero) fails here rather than at commit time.

        Raises:
            ValueError: unsupported type, or invalid operands.
        """
        if not isinstance(calculation_type, str):
            raise ValueError(f"Unsupported calculation type: {calculation_type}")

        calculation_class = _CALCULATION_TYPES.get(calculation_type.strip().lower())
        if calculation_class is None:
            raise ValueError(f"Unsupported calculation type: {calculation_type}")

        calculation = calculation_class(user_id=user_id, a=a, b=b)
        calculation.result = calculation.get_result()
        return calculation

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------
    def _validate_operands(self) -> None:
        for name in ("a", "b"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Operand '{name}' must be a number.")

    def get_result(self) -> float:
        """Compute the result. Each subclass implements its own operation."""
        raise NotImplementedError("Subclasses must implement get_result()")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(a={self.a}, b={self.b}, result={self.result})>"


class Addition(Calculation):
    __mapper_args__ = {"polymorphic_identity": "addition"}

    def get_result(self) -> float:
        self._validate_operands()
        return self.a + self.b


class Subtraction(Calculation):
    __mapper_args__ = {"polymorphic_identity": "subtraction"}

    def get_result(self) -> float:
        self._validate_operands()
        return self.a - self.b


class Multiplication(Calculation):
    __mapper_args__ = {"polymorphic_identity": "multiplication"}

    def get_result(self) -> float:
        self._validate_operands()
        return self.a * self.b


class Division(Calculation):
    __mapper_args__ = {"polymorphic_identity": "division"}

    def get_result(self) -> float:
        self._validate_operands()
        if self.b == 0:
            raise ValueError("Cannot divide by zero.")
        return self.a / self.b


# Registry used by the factory (full names plus short aliases).
_CALCULATION_TYPES = {
    "addition": Addition,
    "add": Addition,
    "subtraction": Subtraction,
    "subtract": Subtraction,
    "sub": Subtraction,
    "multiplication": Multiplication,
    "multiply": Multiplication,
    "division": Division,
    "divide": Division,
}