"""PostgreSQL database implementation for storing price data using SQLAlchemy."""

from datetime import date, datetime
import uuid

from sqlalchemy import (
    UUID,
    BigInteger,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


class DBBacktestJob(Base):
    __tablename__ = "backtest_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, index=True, default=uuid.uuid4
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending", index=True
    )
    # BacktestConfig stored as JSON text
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    backtest_id: Mapped[uuid.UUID] = mapped_column(
        UUID, ForeignKey("backtests.id", ondelete="SET NULL"), nullable=True
    )
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<BacktestJob(id={self.id}, status={self.status})>"


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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        return f"<StockPrice(symbol={self.symbol}, date={self.date})>"


class DBStockPriceMetadata(Base):
    __tablename__ = "stock_price_metadata"

    symbol: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        return (
            f"<StockPriceMetadata(symbol={self.symbol}, fetched_at={self.fetched_at})>"
        )


class DBConstituentChange(Base):
    __tablename__ = "constituent_changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index: Mapped[str] = mapped_column(String, nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    added_symbol: Mapped[str] = mapped_column(String, nullable=True)
    removed_symbol: Mapped[str] = mapped_column(String, nullable=True)

    def __repr__(self) -> str:
        return f"<ConstituentChange(index={self.index}, date={self.date}, added={self.added_symbol}, removed={self.removed_symbol})>"


class DBConstituentMetadata(Base):
    __tablename__ = "constituent_metadata"

    index: Mapped[str] = mapped_column(String, primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        return (
            f"<ConstituentMetadata(index={self.index}, fetched_at={self.fetched_at})>"
        )


class DBStrategy(Base):
    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, index=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    date_start: Mapped[date] = mapped_column(Date, nullable=False)
    date_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="idle", index=True
    )
    final_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_history_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    messages: Mapped[list["DBStrategyMessage"]] = relationship(
        "DBStrategyMessage",
        back_populates="strategy",
        cascade="all, delete-orphan",
        order_by="DBStrategyMessage.sequence",
    )
    backtests: Mapped[list["DBBacktest"]] = relationship(
        "DBBacktest", back_populates="strategy"
    )

    def __repr__(self) -> str:
        return f"<Strategy(id={self.id}, name={self.name}, status={self.status})>"


class DBStrategyMessage(Base):
    __tablename__ = "strategy_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, index=True, default=uuid.uuid4
    )
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("strategies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    strategy: Mapped["DBStrategy"] = relationship(
        "DBStrategy", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<StrategyMessage(id={self.id}, role={self.role}, seq={self.sequence})>"


class DBBacktest(Base):
    __tablename__ = "backtests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, index=True, default=uuid.uuid4
    )
    strategy_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID,
        ForeignKey("strategies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False)
    final_balance: Mapped[float] = mapped_column(Float, nullable=False)
    date_start: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    date_end: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    profit_pct: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_index: Mapped[str] = mapped_column(String, nullable=False)
    baseline_profit_pct: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_profit: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_balance: Mapped[float] = mapped_column(Float, nullable=False)
    # Backtest config stored as JSON
    max_stocks: Mapped[int] = mapped_column(Integer, nullable=False)
    rebalance_interval_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    rule: Mapped[str] = mapped_column(Text, nullable=False)
    index: Mapped[str] = mapped_column(String, nullable=False)
    # Scores stored inline
    scores_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, index=True
    )

    strategy: Mapped["DBStrategy | None"] = relationship(
        "DBStrategy", back_populates="backtests"
    )
    backtest_rebalances: Mapped[list["DBBacktestRebalance"]] = relationship(
        "DBBacktestRebalance", back_populates="backtest", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Backtest(id={self.id}, date_start={self.date_start}, profit_pct={self.profit_pct})>"


class DBBacktestRebalance(Base):
    __tablename__ = "backtest_rebalances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, index=True, default=uuid.uuid4
    )
    backtest_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("backtests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    profit_pct: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_profit_pct: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_profit: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_balance: Mapped[float] = mapped_column(Float, nullable=False)

    backtest: Mapped["DBBacktest"] = relationship(
        "DBBacktest", back_populates="backtest_rebalances"
    )
    backtest_investments: Mapped[list["DBBacktestInvestment"]] = relationship(
        "DBBacktestInvestment",
        back_populates="backtest_rebalance",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BacktestRebalance(id={self.id}, date={self.date}, balance={self.balance})>"


class DBBacktestInvestment(Base):
    __tablename__ = "backtest_investments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID, primary_key=True, index=True, default=uuid.uuid4
    )
    backtest_rebalance_id: Mapped[uuid.UUID] = mapped_column(
        UUID,
        ForeignKey("backtest_rebalances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False, index=True)
    position: Mapped[float] = mapped_column(Float, nullable=False)
    buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    buy_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    sell_price: Mapped[float] = mapped_column(Float, nullable=False)
    sell_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    profit_pct: Mapped[float] = mapped_column(Float, nullable=False)
    profit: Mapped[float] = mapped_column(Float, nullable=False)

    backtest_rebalance: Mapped["DBBacktestRebalance"] = relationship(
        "DBBacktestRebalance", back_populates="backtest_investments"
    )

    def __repr__(self) -> str:
        return f"<BacktestInvestment(id={self.id}, symbol={self.symbol}, profit={self.profit})>"


# =============================================================================
# Stock Metrics Model
# =============================================================================
class DBStockIndicators(Base):
    __tablename__ = "stock_indicators"

    symbol: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    total_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    # Trend metrics (regression-based)
    linear_slope_pct: Mapped[float] = mapped_column(Float, nullable=False)
    linear_r_squared: Mapped[float] = mapped_column(Float, nullable=False)
    log_slope: Mapped[float] = mapped_column(Float, nullable=False)
    log_r_squared: Mapped[float] = mapped_column(Float, nullable=False)
    # Return metrics (point-to-point changes)
    change_1w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    change_2w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    change_4w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    change_13w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    change_26w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    change_1y_pct: Mapped[float] = mapped_column(Float, nullable=False)
    # Volatility metrics (max swings)
    max_jump_1w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_drop_1w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_jump_2w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_drop_2w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_jump_4w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    max_drop_4w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    # Volatility metrics (statistical)
    weekly_return_std: Mapped[float] = mapped_column(Float, nullable=False)
    downside_std: Mapped[float] = mapped_column(Float, nullable=False)
    # Stability metrics
    max_drawdown_pct: Mapped[float] = mapped_column(Float, nullable=False)
    pct_weeks_positive: Mapped[float] = mapped_column(Float, nullable=False)
    slope_13w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared_13w: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared_4w: Mapped[float] = mapped_column(Float, nullable=False)
    slope_26w_pct: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared_26w: Mapped[float] = mapped_column(Float, nullable=False)
    # Momentum shape
    acceleration_13w: Mapped[float] = mapped_column(Float, nullable=False)
    pct_from_4w_high: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        return f"<StockIndicators(symbol={self.symbol}, date={self.date}, slope={self.linear_slope_pct:.2f}%)>"
