
import pandas as pd
from sklearn.linear_model import LogisticRegression

from sklearn.multioutput import MultiOutputClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler


from preprocess import preprocess_data


X_train, y_train, X_test, y_test = preprocess_data(y_output="multilabel")

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