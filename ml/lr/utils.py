import pandas as pd
import numpy as np

from imblearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.impute import SimpleImputer
from imblearn.over_sampling import SMOTE


def one_hot_encode_tags(df, tags_column):
    """
    One-hot encodes comma-separated tags in a DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame containing the tags.
        tags_column (str): The name of the column containing the tags.

    Returns:
        pd.DataFrame: The DataFrame with one-hot encoded tags.
    """
    # Split the comma-separated strings into lists of tags
    df[tags_column] = df[tags_column].str.split(', ')

    # Create a MultiLabelBinarizer object
    mlb = MultiLabelBinarizer()

    # Fit and transform the tags column
    encoded_tags = mlb.fit_transform(df.pop(tags_column))

    # Create a DataFrame with the one-hot encoded tags
    encoded_df = pd.DataFrame(encoded_tags, columns=mlb.classes_, index=df.index)

    # Concatenate the encoded tags with the original DataFrame
    df = df.join(encoded_df)

    return df


