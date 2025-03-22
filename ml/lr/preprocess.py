import os
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder

from utils import one_hot_encode_tags, handle_missing_due_dates, datetime_to_features, priority_to_numeric


X_DROP = ['id', 'create_date', 'due_date', 'title', 'completed_date']

X_CATEGORICAL_FEATURES = ['status', 'recurrence']
Y_CATEGORICAL_FEATURES = ['priority']

COLUMNS_TO_SCALE = [
    #'create_year',
    'create_month',
    'create_day',
    'create_dow',
    'create_doy',
    #'due_year',
    'due_month',
    'due_day',
    'due_dow',
    'due_doy',
    #'completed_year',
    'completed_month',
    'completed_day',
    'completed_dow',
    'completed_doy',
    'num_updated',
    'num_deferred',
    'num_promoted',
    'reminder_days',
    'estimated_effort'
]


def preprocess_data(y_output="multiclass"):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'output')
    df = pd.read_csv(os.path.join(output_dir, "tasks_pred_priority.csv"))

    # fill in null dates
    df = handle_missing_due_dates(df)

    # dates to datetimeformat
    df['create_date'] = pd.to_datetime(df['create_date'], errors='coerce')
    df['due_date'] = pd.to_datetime(df['due_date'], errors='coerce')
    df['completed_date'] = pd.to_datetime(df['completed_date'], errors='coerce')

    # split dates
    df = pd.concat([df, datetime_to_features(df['create_date'], prefix='create_')], axis=1)
    df = pd.concat([df, datetime_to_features(df['due_date'], prefix='due_')], axis=1)
    df = pd.concat([df, datetime_to_features(df['completed_date'], prefix='completed_')], axis=1)

    df[["completed_day", "completed_month", "completed_dow", "completed_doy"]] = df[["completed_day", "completed_month", "completed_dow", "completed_doy"]].fillna(0)

    # categorise Xs
    encoder = OneHotEncoder(sparse_output=False)
    encoded_categorical = encoder.fit_transform(df[X_CATEGORICAL_FEATURES])
    encoded_categorical_df = pd.DataFrame(encoded_categorical,
                                          columns=encoder.get_feature_names_out(X_CATEGORICAL_FEATURES))
    df = pd.concat([df, encoded_categorical_df], axis=1).drop(X_CATEGORICAL_FEATURES, axis=1)

    # categorise Ys
    if y_output == "multiclass":
        df = priority_to_numeric(df)
        y = df["priority"]
        X = df.drop(X_DROP, axis=1)
        X = X.drop(columns="priority", axis=1)
    else:
        encoder = OneHotEncoder(sparse_output=False)
        encoded_categorical = encoder.fit_transform(df[Y_CATEGORICAL_FEATURES])
        encoded_categorical_df = pd.DataFrame(encoded_categorical,
                                              columns=encoder.get_feature_names_out(Y_CATEGORICAL_FEATURES))
        df = pd.concat([df, encoded_categorical_df], axis=1).drop(Y_CATEGORICAL_FEATURES, axis=1)
        pred_columns = [col for col in df.columns if col.startswith('priority_')]
        y = df[pred_columns]
        X = df.drop(X_DROP, axis=1)
        X = X.drop(columns=pred_columns, axis=1)



    X.to_csv(os.path.join(output_dir, "tasks_pred_priority_x.csv"))
    y.to_csv(os.path.join(output_dir, "tasks_pred_priority_y.csv"))

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=99)


    # 1-hot encode tags
    X_train, X_test = one_hot_encode_tags(X_train,X_test,'tags')

    X_train = X_train.drop("tags", axis=1)
    X_test = X_test.drop("tags", axis=1)

    # scale Xs
    scaler = MinMaxScaler()
    X_train[COLUMNS_TO_SCALE] = scaler.fit_transform(X_train[COLUMNS_TO_SCALE])
    X_test[COLUMNS_TO_SCALE] = scaler.transform(X_test[COLUMNS_TO_SCALE])

    return X_train, y_train, X_test, y_test