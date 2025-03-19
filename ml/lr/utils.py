import pandas as pd

from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.preprocessing import OneHotEncoder


def one_hot_encode_tags(df_train, df_test, tags_column, prefix="tag_"):
    """One-hot encodes comma-separated tags in a DataFrame."""

    def preprocess_tags(tags_list):
        """Removes spaces from individual tags."""
        return [tag.strip().replace(' ', '_') for tag in tags_list]

    # Fit MultiLabelBinarizer on training data only
    train_tags = df_train[tags_column].fillna('').apply(lambda x: preprocess_tags(x.split(',')) if x else [])

    mlb = MultiLabelBinarizer()
    mlb.fit(train_tags)

    # Transform train data
    encoded_train_tags = mlb.transform(train_tags)
    encoded_train_df = pd.DataFrame(encoded_train_tags, columns=mlb.classes_, index=df_train.index)
    encoded_train_df.columns = [f"{prefix}{col}" for col in encoded_train_df.columns]
    df_train = df_train.join(encoded_train_df)

    # Transform test data
    test_tags = df_test[tags_column].fillna('').apply(lambda x: preprocess_tags(x.split(',')) if x else [])
    encoded_test_tags = mlb.transform(test_tags)
    encoded_test_df = pd.DataFrame(encoded_test_tags, columns=mlb.classes_, index=df_test.index)
    encoded_test_df.columns = [f"{prefix}{col}" for col in encoded_test_df.columns]
    df_test = df_test.join(encoded_test_df)

    # Store train columns
    train_columns = encoded_train_df.columns

    # Add missing columns to the test data
    for col in train_columns:
        if col not in df_test.columns:
            df_test[col] = 0

    # Ensure test data has the same columns as train data
    #df_test = df_test[train_columns]

    return df_train, df_test


def one_hot_encode_column(df, column_name):
    """One-hot encodes a column."""
    encoder = OneHotEncoder(sparse_output=False, drop=None)
    encoded_values = encoder.fit_transform(df[column_name].values.reshape(-1, 1))
    encoded_df = pd.DataFrame(encoded_values, columns=encoder.get_feature_names_out([column_name]))
    df = pd.concat([df, encoded_df], axis=1).drop(column_name, axis=1)
    return df


def datetime_to_features(dt_series, prefix=''):
    """Transforms datetime objects into numerical features."""
    df_features = pd.DataFrame({
        f'{prefix}year': dt_series.dt.year,
        f'{prefix}month': dt_series.dt.month,
        f'{prefix}day': dt_series.dt.day
    })
    return df_features


def handle_missing_due_dates(df, imputation_date='2025-12-31'):
    """Handles missing due_dates."""
    df['due_date_missing'] = df['due_date'].isnull().astype(int)
    imputation_value = pd.to_datetime(imputation_date)
    df['due_date'] = df['due_date'].fillna(imputation_value)
    df['due_date'] = pd.to_datetime(df['due_date'])
    return df


