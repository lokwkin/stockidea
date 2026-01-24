"""PostgreSQL database implementation for storing price data using SQLAlchemy."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Float,
    Integer,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class DBStockPrice(Base):
    __tablename__ = "stock_prices"

    symbol: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    open: Mapped[float] = mapped_column(Float, nullable=True)
    high: Mapped[float] = mapped_column(Float, nullable=True)
    low: Mapped[float] = mapped_column(Float, nullable=True)
    close: Mapped[float] = mapped_column(Float, nullable=True)
    adj_close: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[BigInteger] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self) -> str:
        return f"<StockPrice(symbol={self.symbol}, date={self.date})>"


class DBStockPriceMetadata(Base):
    __tablename__ = "stock_price_metadata"

    symbol: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self) -> str:
        return f"<StockPriceMetadata(symbol={self.symbol}, fetched_at={self.fetched_at})>"


class DBAnalysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String, index=True)
    analysis_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    analysis_data: Mapped[str] = mapped_column(String, nullable=False)
