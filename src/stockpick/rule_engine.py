"""Rule engine for evaluating string-based filter expressions on TrendAnalysis objects."""

from typing import Callable

from simpleeval import SimpleEval  # type: ignore

from stockpick.types import TrendAnalysis


class RuleEngine:
    """Engine for parsing and evaluating string-based rules on TrendAnalysis objects."""

    def compile(self, rule_string: str) -> Callable[[TrendAnalysis], bool]:
        """
        Compile a string rule into a callable function.

        Args:
            rule_string: String expression like "change_3m_pct > 1 AND biggest_biweekly_drop_pct > 15"

        Returns:
            A callable function that takes TrendAnalysis and returns bool

        Examples:
            >>> engine = RuleEngine()
            >>> rule = engine.compile("change_3m_pct > 1 AND linear_r_squared > 0.8")
            >>> result = rule(analysis)
        """
        # Normalize the rule string (handle case-insensitive AND/OR)
        normalized_rule = self._normalize_rule(rule_string)

        def evaluate(analysis: TrendAnalysis) -> bool:
            """Evaluate the rule against a TrendAnalysis object."""
            # Create a context with all TrendAnalysis attributes
            names = {
                "symbol": analysis.symbol,
                "weeks_above_1_week_ago": analysis.weeks_above_1_week_ago,
                "weeks_above_2_weeks_ago": analysis.weeks_above_2_weeks_ago,
                "weeks_above_4_weeks_ago": analysis.weeks_above_4_weeks_ago,
                "biggest_weekly_jump_pct": analysis.biggest_weekly_jump_pct,
                "biggest_weekly_drop_pct": analysis.biggest_weekly_drop_pct,
                "biggest_biweekly_jump_pct": analysis.biggest_biweekly_jump_pct,
                "biggest_biweekly_drop_pct": analysis.biggest_biweekly_drop_pct,
                "biggest_monthly_jump_pct": analysis.biggest_monthly_jump_pct,
                "biggest_monthly_drop_pct": analysis.biggest_monthly_drop_pct,
                "change_1y_pct": analysis.change_1y_pct,
                "change_6m_pct": analysis.change_6m_pct,
                "change_3m_pct": analysis.change_3m_pct,
                "change_1m_pct": analysis.change_1m_pct,
                "total_weeks": analysis.total_weeks,
                "linear_slope_pct": analysis.linear_slope_pct,
                "linear_r_squared": analysis.linear_r_squared,
                "log_slope": analysis.log_slope,
                "log_r_squared": analysis.log_r_squared,
            }
            try:
                # SimpleEval automatically validates the expression and only allows safe operations
                evaluator = SimpleEval(names=names)
                result = evaluator.eval(normalized_rule)

                # Validate that the result is not a string (simpleeval should catch this, but double-check)
                if isinstance(result, str):
                    raise ValueError(
                        f"Rule '{rule_string}' evaluated to a string '{result}'. "
                        f"Rules must be boolean expressions (e.g., use comparison operators like >, <, ==)."
                    )

                return bool(result)
            except (NameError, AttributeError) as e:
                # These errors indicate invalid field names or attributes
                raise ValueError(
                    f"Error evaluating rule '{rule_string}': {e}. "
                    f"Make sure all field names are valid and the expression syntax is correct."
                ) from e
            except Exception as e:
                # Catch other errors (syntax errors, type errors, etc.)
                raise ValueError(
                    f"Error evaluating rule '{rule_string}': {e}. "
                    f"Make sure all field names are valid and the expression syntax is correct."
                ) from e

        return evaluate

    def _normalize_rule(self, rule_string: str) -> str:
        """
        Normalize the rule string to handle case-insensitive AND/OR.

        Args:
            rule_string: Original rule string

        Returns:
            Normalized rule string with lowercase operators
        """
        import re

        # Replace AND/OR (case-insensitive) with lowercase versions
        # Use word boundaries to avoid replacing parts of words
        normalized = re.sub(r"\bAND\b", "and", rule_string, flags=re.IGNORECASE)
        normalized = re.sub(r"\bOR\b", "or", normalized, flags=re.IGNORECASE)
        return normalized


def compile_rule(rule_string: str) -> Callable[[TrendAnalysis], bool]:
    """
    Convenience function to compile a rule string.

    Args:
        rule_string: String expression like "change_3m_pct > 1 AND biggest_biweekly_drop_pct > 15"

    Returns:
        A callable function that takes TrendAnalysis and returns bool

    Examples:
        >>> rule = compile_rule("change_3m_pct > 1 AND linear_r_squared > 0.8")
        >>> result = rule(analysis)
    """
    engine = RuleEngine()
    return engine.compile(rule_string)
