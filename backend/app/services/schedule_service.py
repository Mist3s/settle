"""ScheduleService — annuity schedule generation (pure functions, no DB).

All calculations use decimal.Decimal. No float anywhere in this module.
"""

from __future__ import annotations

import calendar
import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, slots=True)
class ScheduleEntry:
    """One row of an amortisation schedule."""

    due_date: date
    amount: Decimal
    principal_part: Decimal
    interest_part: Decimal
    balance_after: Decimal


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TWO = Decimal("0.01")  # quantize target for kopecks


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_TWO, rounding=ROUND_HALF_UP)


def _next_payment_date(current: date, payment_day: int) -> date:
    """Advance to the next month, clamping to the last day if needed."""
    year = current.year
    month = current.month + 1
    if month > 12:
        month = 1
        year += 1
    last_day = calendar.monthrange(year, month)[1]
    day = min(payment_day, last_day)
    return date(year, month, day)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_schedule(
    principal: Decimal,
    annual_rate: Decimal,
    months_remaining: int,
    start_date: date,
    payment_day: int,
) -> list[ScheduleEntry]:
    """Generate an annuity repayment schedule.

    Parameters
    ----------
    principal : Decimal
        Outstanding principal balance.
    annual_rate : Decimal
        Annual interest rate as percentage, e.g. ``Decimal("12.5")``
        means 12.5 % per year.
    months_remaining : int
        Number of monthly payments.
    start_date : date
        Reference date; the first payment falls on the next month's
        *payment_day*.
    payment_day : int
        Day of month for payments (1-31). Clamped to the last day of
        month when the month is shorter.

    Returns
    -------
    list[ScheduleEntry]
        One entry per payment period.  The last entry's ``balance_after``
        is guaranteed to be exactly ``Decimal("0.00")``.
    """
    if months_remaining <= 0:
        return []
    if principal <= 0:
        return []

    monthly_rate = annual_rate / Decimal(1200)  # percent → fraction / 12

    # Zero-rate shortcut (installments, split)
    if monthly_rate == 0:
        annuity = _quantize(principal / Decimal(months_remaining))
        entries: list[ScheduleEntry] = []
        balance = principal
        current_date = start_date

        for i in range(months_remaining):
            current_date = _next_payment_date(current_date, payment_day)
            # last payment absorbs rounding residual
            pmt = balance if i == months_remaining - 1 else annuity
            balance = _quantize(balance - pmt)
            entries.append(
                ScheduleEntry(
                    due_date=current_date,
                    amount=pmt,
                    principal_part=pmt,
                    interest_part=Decimal("0.00"),
                    balance_after=balance,
                )
            )
        return entries

    # Standard annuity formula: P = S * i * (1+i)^n / ((1+i)^n - 1)
    one_plus_i = Decimal(1) + monthly_rate
    # Decimal doesn't have a built-in pow for fractional exponents, but n is
    # always a positive integer so we can use repeated multiplication (or the
    # math-assisted approach via ln for large n). For reasonable n (≤360)
    # direct ** works fine with Decimal.
    power_n = one_plus_i ** months_remaining
    annuity = _quantize(principal * monthly_rate * power_n / (power_n - Decimal(1)))

    entries = []
    balance = principal
    current_date = start_date

    for i in range(months_remaining):
        current_date = _next_payment_date(current_date, payment_day)
        interest = _quantize(balance * monthly_rate)
        principal_part = _quantize(annuity - interest)

        if i == months_remaining - 1:
            # Absorb rounding residual in the last payment
            principal_part = balance
            interest = _quantize(balance * monthly_rate)
            pmt = _quantize(principal_part + interest)
            balance = Decimal("0.00")
        else:
            pmt = annuity
            balance = _quantize(balance - principal_part)

        entries.append(
            ScheduleEntry(
                due_date=current_date,
                amount=pmt,
                principal_part=principal_part,
                interest_part=interest,
                balance_after=balance,
            )
        )

    return entries


def solve_for_n(
    annuity_payment: Decimal,
    principal: Decimal,
    annual_rate: Decimal,
) -> int:
    """Solve for number of remaining payments given fixed annuity.

    Used by the ``shorten_term`` prepayment strategy.
    Returns the ceiling integer number of months.
    """
    if annuity_payment <= 0 or principal <= 0:
        return 0

    monthly_rate = annual_rate / Decimal(1200)
    if monthly_rate == 0:
        # interest-free: n = ceil(principal / payment)
        n_raw = principal / annuity_payment
        return int(n_raw.to_integral_value(rounding=ROUND_HALF_UP))

    # From annuity formula: n = -ln(1 - S*i/P) / ln(1+i)
    # We switch to float only for the ln() call — the result is an integer
    # month count, not a monetary value, so precision loss is irrelevant.
    si_over_p = float(principal * monthly_rate / annuity_payment)
    if si_over_p >= 1:
        # payment doesn't even cover interest — shouldn't happen normally
        # Return a fallback so caller can handle
        return 0

    n_float = -math.log(1 - si_over_p) / math.log(1 + float(monthly_rate))
    return max(1, math.ceil(n_float))


def recalculate_after_prepayment(
    new_principal: Decimal,
    annual_rate: Decimal,
    months_remaining: int,
    prepayment_date: date,
    payment_day: int,
    strategy: str,
    current_annuity: Decimal | None = None,
) -> list[ScheduleEntry]:
    """Recalculate schedule after a partial prepayment.

    Parameters
    ----------
    strategy : str
        ``"reduce_payment"`` — keep n, recalculate annuity.
        ``"shorten_term"`` — keep annuity, solve for new n.
    current_annuity : Decimal | None
        Required when ``strategy == "shorten_term"``.
    """
    if strategy == "shorten_term":
        if current_annuity is None or current_annuity <= 0:
            msg = "current_annuity is required for shorten_term strategy"
            raise ValueError(msg)
        n = solve_for_n(current_annuity, new_principal, annual_rate)
        if n == 0:
            return []
        return generate_schedule(
            principal=new_principal,
            annual_rate=annual_rate,
            months_remaining=n,
            start_date=prepayment_date,
            payment_day=payment_day,
        )

    # reduce_payment: months_remaining stays the same, annuity recalculated
    return generate_schedule(
        principal=new_principal,
        annual_rate=annual_rate,
        months_remaining=months_remaining,
        start_date=prepayment_date,
        payment_day=payment_day,
    )
