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


class DBStockSma(Base):
    __tablename__ = "stock_sma"

    symbol: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    period_length: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    date: Mapped[date] = mapped_column(Date, primary_key=True, index=True)
    sma_value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        return (
            f"<StockSma(symbol={self.symbol}, period={self.period_length}, "
            f"date={self.date})>"
        )


class DBStockSmaMetadata(Base):
    __tablename__ = "stock_sma_metadata"

    symbol: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    period_length: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        return (
            f"<StockSmaMetadata(symbol={self.symbol}, period={self.period_length}, "
            f"fetched_at={self.fetched_at})>"
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
    sort_expr: Mapped[str | None] = mapped_column(Text, nullable=True)
    index: Mapped[str] = mapped_column(String, nullable=False)
    # Per-position stop-loss expression (evaluated at buy time); NULL = no stop loss.
    stop_loss_expr: Mapped[str | None] = mapped_column(Text, nullable=True)
    # End-of-period sell convention ("friday_close" | "monday_open").
    sell_timing: Mapped[str | None] = mapped_column(String, nullable=True)
    # Per-fill slippage friction (% of price). NULL on legacy rows.
    slippage_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)

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
    # Slope (linear regression, % per week) per window
    slope_pct_4w: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    slope_pct_13w: Mapped[float] = mapped_column(Float, nullable=False)
    slope_pct_26w: Mapped[float] = mapped_column(Float, nullable=False)
    slope_pct_52w: Mapped[float] = mapped_column(Float, nullable=False)
    # R² (linear regression) per window
    r_squared_4w: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared_13w: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared_26w: Mapped[float] = mapped_column(Float, nullable=False)
    r_squared_52w: Mapped[float] = mapped_column(Float, nullable=False)
    # Log regression slope and R² per window
    log_slope_13w: Mapped[float] = mapped_column(Float, nullable=False)
    log_r_squared_13w: Mapped[float] = mapped_column(Float, nullable=False)
    log_slope_26w: Mapped[float] = mapped_column(Float, nullable=False)
    log_r_squared_26w: Mapped[float] = mapped_column(Float, nullable=False)
    log_slope_52w: Mapped[float] = mapped_column(Float, nullable=False)
    log_r_squared_52w: Mapped[float] = mapped_column(Float, nullable=False)
    # Point-to-point change (%) per window
    change_pct_1w: Mapped[float] = mapped_column(Float, nullable=False)
    change_pct_2w: Mapped[float] = mapped_column(Float, nullable=False)
    change_pct_4w: Mapped[float] = mapped_column(Float, nullable=False)
    change_pct_13w: Mapped[float] = mapped_column(Float, nullable=False)
    change_pct_26w: Mapped[float] = mapped_column(Float, nullable=False)
    change_pct_52w: Mapped[float] = mapped_column(Float, nullable=False)
    # Max single-period jump / drop (%)
    max_jump_pct_1w: Mapped[float] = mapped_column(Float, nullable=False)
    max_drop_pct_1w: Mapped[float] = mapped_column(Float, nullable=False)
    max_jump_pct_2w: Mapped[float] = mapped_column(Float, nullable=False)
    max_drop_pct_2w: Mapped[float] = mapped_column(Float, nullable=False)
    max_jump_pct_4w: Mapped[float] = mapped_column(Float, nullable=False)
    max_drop_pct_4w: Mapped[float] = mapped_column(Float, nullable=False)
    # Weekly return std-dev (full series)
    return_std_52w: Mapped[float] = mapped_column(Float, nullable=False)
    downside_std_52w: Mapped[float] = mapped_column(Float, nullable=False)
    # Max peak-to-trough drawdown (positive %) per window
    max_drawdown_pct_4w: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown_pct_13w: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown_pct_26w: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown_pct_52w: Mapped[float] = mapped_column(Float, nullable=False)
    # Fraction of up-weeks (0.0–1.0) per window
    pct_weeks_positive_4w: Mapped[float] = mapped_column(Float, nullable=False)
    pct_weeks_positive_13w: Mapped[float] = mapped_column(Float, nullable=False)
    pct_weeks_positive_26w: Mapped[float] = mapped_column(Float, nullable=False)
    pct_weeks_positive_52w: Mapped[float] = mapped_column(Float, nullable=False)
    # Momentum shape
    acceleration_pct_4w: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    acceleration_pct_13w: Mapped[float] = mapped_column(Float, nullable=False)
    acceleration_pct_26w: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    acceleration_pct_52w: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    from_high_pct_4w: Mapped[float] = mapped_column(Float, nullable=False)
    # Moving average structure (price relative to SMA, %)
    price_vs_ma20_pct: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    price_vs_ma50_pct: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    price_vs_ma100_pct: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    price_vs_ma200_pct: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    ma50_vs_ma200_pct: Mapped[float] = mapped_column(
        Float, nullable=False, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    def __repr__(self) -> str:
        return f"<StockIndicators(symbol={self.symbol}, date={self.date}, slope_52w={self.slope_pct_52w:.2f}%)>"
