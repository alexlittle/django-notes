import datetime
import os
import joblib
import numpy as np
import pandas as pd
import torch

from ffnn import FFNN
from utils import NUMERICAL_FEATURES, CATEGORICAL_FEATURES, get_sentence_embedding_model


base_dir = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(base_dir, 'output')

t_model = get_sentence_embedding_model(output_dir)
loaded_scaler = joblib.load(os.path.join(output_dir, 'minmax_scaler.joblib'))
cat_encoder = joblib.load(os.path.join(output_dir, 'cat_encoder.joblib'))

input_data = {
    'current_date': datetime.datetime.now(),
    'title': "juliette",
    'status': "open",
    'priority': "medium",
    'recurrence': "none",
    'reminder_days': -1 ,
    'tags': "personal, email",
    'completed_date_dow': -1 ,
    'completed_date_dom': -1 ,
    'completed_date_m': -1 ,
    'completed_date_doy': -1
}

input_df = pd.DataFrame([input_data])

# Extract date components
input_df['current_date_dow'] = input_df['current_date'].dt.dayofweek
input_df['current_date_dom'] = input_df['current_date'].dt.day
input_df['current_date_m'] = input_df['current_date'].dt.month
input_df['current_date_doy'] = input_df['current_date'].dt.dayofyear

numerical_input_df = input_df[NUMERICAL_FEATURES] #keep as a dataframe.


# Scale numerical features
scaled_numerical_input = loaded_scaler.transform(numerical_input_df)

# One-hot encode categorical features
categorical_input = input_df[CATEGORICAL_FEATURES]
encoded_categorical_input = cat_encoder.transform(categorical_input)

# Generate sentence embeddings
title_embedding = t_model.encode([input_data['title']])
tags_embedding = t_model.encode([input_data['tags']])

# Concatenate features
model_input = np.concatenate(
    (scaled_numerical_input, encoded_categorical_input, title_embedding, tags_embedding), axis=1
)
# Convert to tensor
model_input_tensor = torch.tensor(model_input, dtype=torch.float32)

print(model_input_tensor.shape)
input_size = model_input_tensor.shape[1]
num_categories = 5
loaded_model = FFNN(input_size, num_categories) #create an instance of the model.
loaded_model.load_state_dict(torch.load(os.path.join(output_dir,'notes_model.pt')))
loaded_model.eval() #set to evaluation mode.

show_reminder_pred, due_pred = loaded_model(model_input_tensor)

sigmoid = torch.nn.Sigmoid()
probabilities = sigmoid(show_reminder_pred)

# Apply threshold (e.g., 0.5)
threshold = 0.5
binary_prediction = (probabilities >= threshold).int()
print("Show Reminder Prediction:", binary_prediction.item())

predicted_class_index = torch.argmax(due_pred).item()

# Create a one-hot encoded vector
one_hot_vector = np.zeros((1, num_categories)) #create a 2d array.
one_hot_vector[0, predicted_class_index] = 1 #set the predicted class to 1.

decoded_due_label = due_encoder.inverse_transform(one_hot_vector)[0][0]

# Print the decoded label
print("Decoded Due Label:", decoded_due_label)
