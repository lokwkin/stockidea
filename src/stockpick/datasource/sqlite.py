"""SQLite cache implementation for storing price data using SQLAlchemy."""

from datetime import date, datetime, timedelta

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
    delete,
    select,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from stockpick.config import CACHE_DIR
from stockpick.types import FMPAdjustedStockPrice, StockPrice


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
    volume: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self) -> str:
        return f"<StockPrice(symbol={self.symbol}, date={self.date})>"


class DBStockPriceMetadata(Base):
    __tablename__ = "stock_price_metadata"

    symbol: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self) -> str:
        return f"<StockPriceMetadata(symbol={self.symbol}, fetched_at={self.fetched_at})>"


_engine = None
_SessionLocal = None


def _get_engine():
    """Get SQLAlchemy engine for the cache database."""
    global _engine
    if _engine is None:
        CACHE_DIR.mkdir(exist_ok=True)
        db_path = CACHE_DIR / "fmp_cache.sqlite3"
        _engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(_engine)
    return _engine


def _get_sessionmaker():
    """Get SQLAlchemy sessionmaker."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = _get_engine()
        _SessionLocal = sessionmaker(bind=engine)
    return _SessionLocal


# Global session for the database
_DB_SESSION: Session | None = None


def get_db_session() -> Session:
    global _DB_SESSION
    if _DB_SESSION is None:
        SessionLocal = _get_sessionmaker()
        _DB_SESSION = SessionLocal()
    return _DB_SESSION


def save_stock_prices(db_session: Session, symbol: str, prices: list[FMPAdjustedStockPrice]) -> None:

    # Delete existing entries for this symbol
    delete_prices_stmt = delete(DBStockPrice).where(DBStockPrice.symbol == symbol.upper())
    delete_metadata_stmt = delete(DBStockPriceMetadata).where(DBStockPriceMetadata.symbol == symbol.upper())
    db_session.execute(delete_prices_stmt)
    db_session.execute(delete_metadata_stmt)
    db_session.commit()

    # Insert new entries
    for price_data in prices:
        price_record = DBStockPrice(
            symbol=symbol.upper(),
            date=date.fromisoformat(price_data.date),
            open=price_data.adjOpen,
            high=price_data.adjHigh,
            low=price_data.adjLow,
            close=price_data.adjClose,
            adj_close=price_data.adjClose,
            volume=price_data.volume,
            created_at=datetime.now(),
        )
        db_session.add(price_record)

    # Update metadata for this symbol
    metadata = DBStockPriceMetadata(
        symbol=symbol.upper(),
        fetched_at=datetime.now(),
    )
    db_session.add(metadata)

    db_session.commit()


def is_data_fresh(db_session: Session, symbol: str) -> bool:
    stmt = select(DBStockPriceMetadata).where(DBStockPriceMetadata.symbol == symbol.upper())
    metadata = db_session.execute(stmt).scalar_one_or_none()
    # if the symbol prices are last fetched more than 1 day ago, return False
    if metadata is None:
        return False

    return metadata.fetched_at > datetime.now() - timedelta(days=1)


def get_stock_prices_by_date_range(db_session: Session, symbol: str, from_date: date, to_date: date) -> list[StockPrice]:
    """
    Get the stock prices for a given symbol and date range.
    """
    stmt = select(DBStockPrice).where(DBStockPrice.symbol == symbol.upper()).where(
        DBStockPrice.date >= from_date).where(DBStockPrice.date <= to_date).order_by(DBStockPrice.date.desc())
    prices = list(db_session.execute(stmt).scalars().all())
    return [StockPrice(
        symbol=price.symbol,
        date=price.date,
        adj_close=price.adj_close
    ) for price in prices]


def get_stock_price_by_date(db_session: Session, symbol: str, target_date: date, nearest: bool = False) -> StockPrice:
    """
    Get the stock price for a given symbol and date.
    If nearest is True, and the price is not found for the given date, return the price for the nearest date before the given date.
    """
    stmt = select(DBStockPrice).where(DBStockPrice.symbol == symbol.upper()).where(
        DBStockPrice.date == target_date).order_by(DBStockPrice.date.desc())
    price = db_session.execute(stmt).scalar_one_or_none()
    if price is not None:
        return StockPrice(
            symbol=price.symbol,
            date=price.date,
            adj_close=price.adj_close
        )
    if nearest:
        # Find the price of nearest date we have before the target date
        stmt = select(DBStockPrice).where(DBStockPrice.symbol == symbol.upper()).where(
            DBStockPrice.date < target_date).order_by(DBStockPrice.date.desc()).limit(1)
        price = db_session.execute(stmt).scalar_one_or_none()
        if price is not None:
            return StockPrice(
                symbol=price.symbol,
                date=price.date,
                adj_close=price.adj_close
            )

    raise ValueError(f"No price data available for symbol: {symbol} on date: {target_date}")
