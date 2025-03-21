import os
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder, StandardScaler

from utils import one_hot_encode_tags, handle_missing_due_dates, datetime_to_features

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

print(X_train.info())
print(X_test.info())
model = MultiOutputClassifier(LogisticRegression(random_state=99))
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)

for i in range(y_test.shape[1]):
    print(f"Label {i+1} Accuracy:", accuracy_score(y_test.iloc[:, i], y_pred[:, i]))
    print(f"Label {i+1} Classification Report:\n", classification_report(y_test.iloc[:, i], y_pred[:, i]))

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)

# Get the coefficients from the multioutput model.
coefficients = []
for estimator in model.estimators_:
    coefficients.append(estimator.coef_.flatten())

# Create a DataFrame to display coefficients
coef_df = pd.DataFrame(coefficients, columns=X_train.columns)

# Print the coefficients
print("Coefficients:")
print(coef_df)

# Print the absolute value of the coefficients, to see the magnitude of the impact.
print("\nAbsolute Coefficients:")
print(coef_df.abs())

mean_abs_coef = coef_df.abs().mean()
# Print the mean of the absolute coefficients, to see the average impact of each column.
print("\nMean Absolute Coefficients:")
print(mean_abs_coef)

sorted_coef = mean_abs_coef.sort_values(ascending=False)

# Get the top 10 coefficients
top_10_coef = sorted_coef.head(10)

# Print the top 10 coefficients
print("Top 10 Coefficients Influencing Categorization:")
print(top_10_coef)

# If you want to see the actual coefficient values, not just the mean absolute:
print("\nTop 10 Columns and their Coefficients:")
for col_name in top_10_coef.index:
    print(f"\n{col_name}:")
    print(coef_df[col_name])

sorted_coef = mean_abs_coef.sort_values(ascending=True)

# Get the top 10 coefficients
bottom_10_coef = sorted_coef.head(10)

# Print the top 10 coefficients
print("Bottom 10 Coefficients Influencing Categorization:")
print(bottom_10_coef)

# If you want to see the actual coefficient values, not just the mean absolute:
print("\nBottom 10 Columns and their Coefficients:")
for col_name in bottom_10_coef.index:
    print(f"\n{col_name}:")
    print(coef_df[col_name])

#To use the model to predict new data.
#Example new data.
'''
new_data = np.array([[3,2],[1,2]])
new_data_scaled = scaler.transform(new_data)
new_predictions = model.predict(new_data_scaled)
print("New Predictions:", new_predictions)
'''