import json
from decimal import Decimal
from datetime import datetime


def json_me(columns, datasets, index_column=0):
    """
    Converts datasets to a JSON structure with the specified index column as the key.

    Parameters:
        columns (list): List of column names.
        datasets (list of tuples or a single tuple): The data rows.
        index_column (int or str): The column to use as the index (can be column name or index position).

    Returns:
        str: JSON string representation of the data.
    """
    # Ensure datasets is always a list of tuples
    if isinstance(datasets, tuple):
        datasets = [datasets]

    # Determine the index column position
    if isinstance(index_column, int):
        index_pos = index_column
    elif isinstance(index_column, str):
        if index_column in columns:
            index_pos = columns.index(index_column)
        else:
            raise ValueError(f"Column '{index_column}' not found in columns.")
    else:
        raise TypeError("index_column must be an integer or a string.")

    # Create the JSON-friendly dictionary
    result = {
        str(row[index_pos]) if isinstance(row[index_pos], (datetime, Decimal)) else row[index_pos]: {
            col: (
                float(value) if isinstance(value, Decimal) else
                str(value) if isinstance(value, datetime) else
                value
            )
            for col, value in zip(columns, row)
            if col != columns[index_pos]
        }
        for row in datasets
    }

    # Convert to JSON
    return json.dumps(result, indent=4)
