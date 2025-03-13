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


def smote_multi_output(X_train, y_train, random_state=42):
    X_resampled_list = []
    y_resampled_list = []

    for col in y_train.columns:
        smote = SMOTE(random_state=random_state, k_neighbors=2)

        # Fit SMOTE for the current target column
        X_resampled, y_resampled = smote.fit_resample(X_train, y_train[col])

        # Store results
        X_resampled_list.append(pd.DataFrame(X_resampled, columns=X_train.columns))
        y_resampled_list.append(pd.Series(y_resampled, name=col))

    # Combine resampled data
    X_train_resampled = pd.concat(X_resampled_list, ignore_index=True)
    y_train_resampled = pd.concat(y_resampled_list, axis=1)

    imputer = SimpleImputer(strategy='most_frequent')
    y_train_resampled = pd.DataFrame(imputer.fit_transform(y_train_resampled), columns=y_train.columns)
    y_train_resampled = y_train_resampled.round().astype(int)

    return X_train_resampled, y_train_resampled
