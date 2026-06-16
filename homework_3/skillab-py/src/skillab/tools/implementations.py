"""
Tool implementations — funcțiile efective ale tool-urilor.

Convenție: toate tools primesc params cu `input_dfs` (lista de DataFrames) + parametri specifici.
"""
import pandas as pd

from .registry import register_tool
from .params import JoinDataParams, FilterDataParams


@register_tool
def join_data(params: JoinDataParams) -> pd.DataFrame:
    """
    Combină două DataFrames pe baza unei chei comune (join).
    Suportă inner, left, right, outer join.

    TODO: Implementează folosind pandas merge().

    Args:
        params.input_dfs: [left_df, right_df]
        params.left_key: coloana cheie din primul DataFrame
        params.right_key: coloana cheie din al doilea DataFrame
        params.how: tipul de join

    Returns:
        DataFrame rezultat după join
    """
    left_df = params.input_dfs[0]
    right_df = params.input_dfs[1]
    return pd.merge(
        left_df,
        right_df,
        left_on=params.left_key,
        right_on=params.right_key,
        how=params.how,
    )


@register_tool
def filter_data(params: FilterDataParams) -> pd.DataFrame:
    """
    Filtrează un DataFrame pe baza unei condiții.
    Suportă operatori: ==, !=, >, <, >=, <=, contains.

    TODO: Implementează folosind pandas boolean indexing.

    Args:
        params.input_dfs: [df]
        params.column: coloana pe care se aplică filtrul
        params.operator: operatorul de comparație
        params.value: valoarea pentru comparație

    Returns:
        DataFrame filtrat
    """
    df = params.input_dfs[0]
    col = df[params.column]
    op = params.operator
    val = params.value

    if op == "contains":
        mask = col.astype(str).str.contains(val, case=False, na=False)
    elif op in (">", "<", ">=", "<="):
        # Numeric comparison: coerce both column and value to numbers.
        numeric_col = pd.to_numeric(col, errors="coerce")
        numeric_val = float(val)
        if op == ">":
            mask = numeric_col > numeric_val
        elif op == "<":
            mask = numeric_col < numeric_val
        elif op == ">=":
            mask = numeric_col >= numeric_val
        else:
            mask = numeric_col <= numeric_val
    else:  # "==" or "!="
        # Compare numerically when the column is numeric, otherwise as strings.
        if pd.api.types.is_numeric_dtype(col):
            try:
                cmp_val = float(val)
            except ValueError:
                cmp_val = val
            mask = col == cmp_val if op == "==" else col != cmp_val
        else:
            mask = col.astype(str) == val if op == "==" else col.astype(str) != val

    return df[mask]
