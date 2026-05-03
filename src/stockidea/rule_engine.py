"""Rule engine for evaluating string-based filter expressions on StockIndicators objects."""

import re
from typing import Callable

from simpleeval import SimpleEval  # type: ignore

from stockidea.types import StockIndicators


DEFAULT_SORT = "change_pct_13w / return_std_52w"

# Safe builtins exposed to user-written expressions (rules, sort, stop-loss).
# simpleeval's defaults omit these; we whitelist a small read-only set.
SAFE_FUNCTIONS: dict[str, Callable] = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}


class RuleEngine:
    """Engine for parsing and evaluating string-based rules on StockIndicators objects."""

    @staticmethod
    def _get_trend_analysis_field_names() -> set[str]:
        """
        Dynamically extract field names from the StockIndicators Pydantic v2 model.

        Returns:
            Set of valid StockIndicators field names
        """
        return set(StockIndicators.model_fields.keys())

    def compile(self, rule_string: str) -> Callable[[StockIndicators], bool]:
        """
        Compile a string rule into a callable function.

        Args:
            rule_string: String expression like "change_pct_13w > 1 AND max_drop_pct_2w > 15"

        Returns:
            A callable function that takes StockIndicators and returns bool

        Examples:
            >>> engine = RuleEngine()
            >>> rule = engine.compile("change_pct_13w > 1 AND r_squared_52w > 0.8")
            >>> result = rule(analysis)
        """
        # Normalize the rule string (handle case-insensitive AND/OR)
        normalized_rule = self._normalize_rule(rule_string)

        def evaluate(analysis: StockIndicators) -> bool:
            """Evaluate the rule against a StockIndicators object."""
            # Create a context with all StockIndicators attributes dynamically
            # Use getattr to safely access fields, falling back to model_dump for compatibility
            field_names = self._get_trend_analysis_field_names()
            names = {
                field_name: getattr(analysis, field_name) for field_name in field_names
            }
            try:
                # SimpleEval automatically validates the expression and only allows safe operations
                evaluator = SimpleEval(names=names, functions=SAFE_FUNCTIONS)
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
        # Replace AND/OR (case-insensitive) with lowercase versions
        # Use word boundaries to avoid replacing parts of words
        normalized = re.sub(r"\bAND\b", "and", rule_string, flags=re.IGNORECASE)
        normalized = re.sub(r"\bOR\b", "or", normalized, flags=re.IGNORECASE)
        return normalized

    def extract_involved_keys(self, rule_string: str) -> list[str]:
        """
        Extract the StockIndicators keys that are referenced in the rule string.

        Args:
            rule_string: String expression like "change_pct_13w > 1 AND max_drop_pct_2w > 15"

        Returns:
            List of StockIndicators field names that are used in the rule

        Examples:
            >>> engine = RuleEngine()
            >>> keys = engine.extract_involved_keys("change_pct_13w > 1 AND r_squared_52w > 0.8")
            >>> print(keys)
            ['change_pct_13w', 'r_squared_52w']
        """
        # Dynamically get all valid StockIndicators field names
        valid_keys = self._get_trend_analysis_field_names()

        # Normalize the rule string
        normalized = self._normalize_rule(rule_string)

        # Find all identifiers in the rule string
        # Match valid Python identifiers (word characters and underscores)
        # Use word boundaries to avoid partial matches
        pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"
        matches = re.findall(pattern, normalized)

        # Filter to only include valid StockIndicators keys
        involved_keys = [key for key in matches if key in valid_keys]

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for key in involved_keys:
            if key not in seen:
                seen.add(key)
                result.append(key)

        return result


def compile_sort(sort_expr: str) -> Callable[[StockIndicators], float]:
    """
    Compile a sort expression string into a callable that returns a numeric score.

    The expression uses StockIndicators field names and arithmetic operators.
    Higher scores rank higher. Stocks where evaluation fails (e.g. division by zero)
    receive -inf.

    Args:
        sort_expr: Arithmetic expression like "change_pct_13w / return_std_52w"

    Returns:
        A callable that takes StockIndicators and returns a float score.

    Examples:
        >>> rank = compile_sort("change_pct_13w / return_std_52w")
        >>> score = rank(indicators)
    """
    field_names = set(StockIndicators.model_fields.keys())

    def evaluate(indicators: StockIndicators) -> float:
        names = {name: getattr(indicators, name) for name in field_names}
        try:
            evaluator = SimpleEval(names=names, functions=SAFE_FUNCTIONS)
            result = evaluator.eval(sort_expr)
            return float(result)
        except Exception:
            return float("-inf")

    return evaluate


def compile_rule(rule_string: str) -> Callable[[StockIndicators], bool]:
    """
    Convenience function to compile a rule string.

    Args:
        rule_string: String expression like "change_pct_13w > 1 AND max_drop_pct_2w > 15"

    Returns:
        A callable function that takes StockIndicators and returns bool

    Examples:
        >>> rule = compile_rule("change_pct_13w > 1 AND r_squared_52w > 0.8")
        >>> result = rule(analysis)
    """
    engine = RuleEngine()
    return engine.compile(rule_string)


def extract_involved_keys(rule_string: str) -> list[str]:
    """
    Convenience function to extract StockIndicators keys from a rule string.

    Args:
        rule_string: String expression like "change_pct_13w > 1 AND max_drop_pct_2w > 15"

    Returns:
        List of StockIndicators field names that are used in the rule

    Examples:
        >>> keys = extract_involved_keys("change_pct_13w > 1 AND r_squared_52w > 0.8")
        >>> print(keys)
        ['change_pct_13w', 'r_squared_52w']
    """
    engine = RuleEngine()
    return engine.extract_involved_keys(rule_string)
