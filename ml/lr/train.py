import os
import pandas as pd
import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler, MinMaxScaler, OneHotEncoder, MultiLabelBinarizer

from utils import one_hot_encode_tags

NUMERICAL_FEATURES = ['current_date_dow',
                      'current_date_dom',
                      'current_date_m',
                      'current_date_doy',
                      "completed_date_dow",
                      "completed_date_dom",
                      "completed_date_m",
                      "completed_date_doy"
                      ]
CATEGORICAL_FEATURES = ['status', 'priority','recurrence']
OUTPUT_FIELDS = [ "due_today" , "due_tomorrow", "due_next_week", "due_next_month", "due_later" ]



base_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(base_dir, 'output')
df = pd.read_csv(os.path.join(output_dir, "tasks.csv"))


scaler = MinMaxScaler()
df[NUMERICAL_FEATURES] = scaler.fit_transform(df[NUMERICAL_FEATURES])
joblib.dump(scaler, os.path.join(output_dir,'minmax_scaler.joblib'))


encoder = OneHotEncoder(sparse_output=False)
encoded_categorical = encoder.fit_transform(df[CATEGORICAL_FEATURES])
encoded_categorical_df = pd.DataFrame(encoded_categorical,
                                      columns=encoder.get_feature_names_out(CATEGORICAL_FEATURES))
df = pd.concat([df, encoded_categorical_df], axis=1).drop(CATEGORICAL_FEATURES, axis=1)
joblib.dump(encoder, os.path.join(output_dir,'cat_encoder.joblib'))

df = one_hot_encode_tags(df, 'tags')

X = df.drop(OUTPUT_FIELDS, axis=1)
#X = X.drop("tags", axis=1)
X = X.drop("days_until_due", axis=1)
y = df[OUTPUT_FIELDS]

# Split data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(y_train.isnull().sum())


# Create and train the logistic regression model
model = MultiOutputClassifier(LogisticRegression(random_state=42)) #sets a random state to produce the same results each time.
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)

for i in range(y_test.shape[1]):
    print(f"Label {i+1} Accuracy:", accuracy_score(y_test.iloc[:, i], y_pred[:, i]))
    print(f"Label {i+1} Classification Report:\n", classification_report(y_test.iloc[:, i], y_pred[:, i]))

#To use the model to predict new data.
#Example new data.
'''
new_data = np.array([[3,2],[1,2]])
new_data_scaled = scaler.transform(new_data)
new_predictions = model.predict(new_data_scaled)
print("New Predictions:", new_predictions)
'''