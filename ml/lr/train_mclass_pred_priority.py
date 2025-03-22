
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from preprocess import preprocess_data


X_train, y_train, X_test, y_test = preprocess_data()

print(X_train.info())
print(X_test.info())
model = LogisticRegression(multi_class='multinomial', solver='lbfgs', max_iter=1000)
model.fit(X_train, y_train)

# Make predictions
y_pred = model.predict(X_test)

print("Accuracy:", accuracy_score(y_test, y_pred))
print("Classification Report:\n", classification_report(y_test, y_pred))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))

# Coefficient Analysis (for Logistic Regression)
if isinstance(model, LogisticRegression):  # Check if the model is LogisticRegression
    coefficients = model.coef_  # Access coefficients directly

    coef_df = pd.DataFrame(coefficients, columns=X_train.columns)

    print("\nCoefficients:")
    print(coef_df)

    abs_coef_df = coef_df.abs()
    print("\nAbsolute Coefficients:")
    print(abs_coef_df)

    mean_abs_coef = abs_coef_df.mean()
    print("\nMean Absolute Coefficients:")
    print(mean_abs_coef)

    sorted_coef = mean_abs_coef.sort_values(ascending=False)
    top_10_coef = sorted_coef.head(10)
    print("\nTop 10 Coefficients Influencing Categorization:")
    print(top_10_coef)

    print("\nTop 10 Columns and their Coefficients:")
    for col_name in top_10_coef.index:
        print(f"\n{col_name}:")
        print(coef_df[col_name])

    sorted_coef = mean_abs_coef.sort_values(ascending=True)
    bottom_10_coef = sorted_coef.head(10)
    print("\nBottom 10 Coefficients Influencing Categorization:")
    print(bottom_10_coef)

    print("\nBottom 10 Columns and their Coefficients:")
    for col_name in bottom_10_coef.index:
        print(f"\n{col_name}:")
        print(coef_df[col_name])

else :
    print("Coefficient analysis is only applicable for Logistic Regression")