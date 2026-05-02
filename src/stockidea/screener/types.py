"""Pydantic models for the screener module."""

from pydantic import BaseModel, Field

from stockidea.types import StockIndicators


class Holding(BaseModel):
    symbol: str
    quantity: int = Field(gt=0)


class Portfolio(BaseModel):
    cash: float = Field(ge=0)
    holdings: list[Holding] = []


class Pick(BaseModel):
    symbol: str
    indicators: StockIndicators
    buy_price: float
    target_quantity: int | None = None
    stop_loss_price: float | None = None


class OrderItem(BaseModel):
    symbol: str
    quantity: int
    price: float | None = None
    stop_loss_price: float | None = None


class ScreenerResult(BaseModel):
    picks: list[Pick]
    sells: list[OrderItem] = []
    buys: list[OrderItem] = []
