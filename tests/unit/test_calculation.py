# tests/unit/test_calculation.py
"""Unit tests for the Calculation model, subclasses, and factory (no DB needed)."""

import uuid

import pytest

# Import User so SQLAlchemy can resolve relationship("User") when mappers configure.
from app.models.user import User  # noqa: F401
from app.models.calculation import (
    Calculation,
    Addition,
    Subtraction,
    Multiplication,
    Division,
)


def uid():
    return uuid.uuid4()


# ---------------------------------------------------------------- operations
@pytest.mark.parametrize(
    "cls, a, b, expected",
    [
        (Addition, 10, 5, 15),
        (Addition, -2, -3, -5),
        (Addition, 1.5, 2.25, 3.75),
        (Subtraction, 10, 4, 6),
        (Subtraction, 0, 5, -5),
        (Multiplication, 3, 4, 12),
        (Multiplication, -2, 5, -10),
        (Multiplication, 0, 99, 0),
        (Division, 10, 2, 5),
        (Division, -9, 3, -3),
        (Division, 0, 7, 0),
    ],
)
def test_get_result(cls, a, b, expected):
    calc = cls(user_id=uid(), a=a, b=b)
    assert calc.get_result() == pytest.approx(expected)


def test_division_by_zero():
    calc = Division(user_id=uid(), a=10, b=0)
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        calc.get_result()


@pytest.mark.parametrize("cls", [Addition, Subtraction, Multiplication, Division])
@pytest.mark.parametrize("a, b", [("x", 1), (1, "y"), (None, 2), (True, 2)])
def test_non_numeric_operands_rejected(cls, a, b):
    calc = cls(user_id=uid(), a=a, b=b)
    with pytest.raises(ValueError, match="must be a number"):
        calc.get_result()


def test_base_class_get_result_not_implemented():
    calc = Calculation(user_id=uid(), a=1, b=2)
    with pytest.raises(NotImplementedError):
        calc.get_result()


def test_repr():
    calc = Addition(user_id=uid(), a=1, b=2)
    calc.result = 3
    text = repr(calc)
    assert "Addition" in text and "a=1" in text and "b=2" in text


# ------------------------------------------------------------------- factory
@pytest.mark.parametrize(
    "name, cls, a, b, expected",
    [
        ("addition", Addition, 2, 3, 5),
        ("add", Addition, 2, 3, 5),
        ("subtraction", Subtraction, 9, 4, 5),
        ("subtract", Subtraction, 9, 4, 5),
        ("sub", Subtraction, 9, 4, 5),
        ("multiplication", Multiplication, 3, 4, 12),
        ("multiply", Multiplication, 3, 4, 12),
        ("division", Division, 8, 2, 4),
        ("divide", Division, 8, 2, 4),
    ],
)
def test_factory_returns_correct_subclass_and_stores_result(name, cls, a, b, expected):
    calc = Calculation.create(name, uid(), a, b)
    assert isinstance(calc, cls)
    assert isinstance(calc, Calculation)
    assert calc.result == pytest.approx(expected)


def test_factory_sets_discriminator_type():
    assert Calculation.create("add", uid(), 1, 2).type == "addition"
    assert Calculation.create("divide", uid(), 4, 2).type == "division"


def test_factory_is_case_insensitive_and_strips_whitespace():
    for name in ["ADD", "Add", "  add  ", "AdDiTiOn"]:
        assert isinstance(Calculation.create(name, uid(), 1, 2), Addition)


def test_factory_invalid_type():
    with pytest.raises(ValueError, match="Unsupported calculation type"):
        Calculation.create("modulus", uid(), 10, 3)


@pytest.mark.parametrize("bad_type", [None, 123, ["add"]])
def test_factory_non_string_type(bad_type):
    with pytest.raises(ValueError, match="Unsupported calculation type"):
        Calculation.create(bad_type, uid(), 1, 2)


def test_factory_divide_by_zero_fails_at_creation():
    with pytest.raises(ValueError, match="Cannot divide by zero."):
        Calculation.create("divide", uid(), 5, 0)


def test_factory_invalid_operand():
    with pytest.raises(ValueError, match="must be a number"):
        Calculation.create("add", uid(), "one", 2)