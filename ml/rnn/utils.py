import os
import torch
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer

NUMERICAL_FEATURES = ['current_date_dow', 'current_date_dom', 'current_date_m', 'current_date_doy']
                      # 'completed_date_dow', 'completed_date_dom', 'completed_date_m', 'completed_date_doy']
CATEGORICAL_FEATURES = ['status', 'priority', 'recurrence']
OUTPUTS = [ "due_today" , "due_tomorrow", "due_next_week", "due_next_month", "due_later" ]

# create train/dev/test
def get_data_pred_due(input_file):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'output')
    df = pd.read_csv(os.path.join(output_dir, input_file))
    df[NUMERICAL_FEATURES] = df[NUMERICAL_FEATURES].astype('float64')

    unique_task_ids = df["id"].unique()

    print(len(unique_task_ids))
    train_ids, test_ids = train_test_split(unique_task_ids, test_size=0.2, random_state=42)
    test_df = df[df["id"].isin(test_ids)]


    train_ids, val_ids = train_test_split(train_ids, test_size=0.1,  random_state=42)
    train_df = df[df["id"].isin(train_ids)]
    val_df = df[df["id"].isin(val_ids)]

    print(len(train_ids))
    print(len(test_ids))
    print(len(val_ids))

    train_df.to_csv(os.path.join(output_dir, 'train.csv'), index=False)
    val_df.to_csv(os.path.join(output_dir, 'val.csv'), index=False)
    test_df.to_csv(os.path.join(output_dir, 'test.csv'), index=False)
    # Preprocessing (Scaling and Encoding)
    # Numerical Features (Scaling)
    scaler = MinMaxScaler()
    train_df.loc[:, NUMERICAL_FEATURES] = scaler.fit_transform(train_df[NUMERICAL_FEATURES])
    val_df.loc[:, NUMERICAL_FEATURES] = scaler.transform(val_df[NUMERICAL_FEATURES])
    test_df.loc[:, NUMERICAL_FEATURES] = scaler.transform(test_df[NUMERICAL_FEATURES])
    joblib.dump(scaler, os.path.join(output_dir,'minmax_scaler.joblib')) #Saving the scaler after fitting it to the training data.

    # Categorical Features (One-Hot Encoding)
    encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore') #Handle unknown categories.
    encoder.fit(df[CATEGORICAL_FEATURES]) #Fit on all categories.
    joblib.dump(encoder, os.path.join(output_dir,'cat_encoder.joblib')) #Saving the encoder after fitting it to all of the data.

    encoded_categorical_train = encoder.transform(train_df[CATEGORICAL_FEATURES])
    encoded_categorical_val = encoder.transform(val_df[CATEGORICAL_FEATURES])
    encoded_categorical_test = encoder.transform(test_df[CATEGORICAL_FEATURES])

    encoded_categorical_train_df = pd.DataFrame(encoded_categorical_train, columns=encoder.get_feature_names_out(CATEGORICAL_FEATURES))
    encoded_categorical_dev_df = pd.DataFrame(encoded_categorical_val, columns=encoder.get_feature_names_out(CATEGORICAL_FEATURES))
    encoded_categorical_test_df = pd.DataFrame(encoded_categorical_test, columns=encoder.get_feature_names_out(CATEGORICAL_FEATURES))

    # Sentence Embeddings
    t_model = get_sentence_embedding_model(output_dir)
    train_title_embeddings = t_model.encode(train_df['title'].tolist())
    train_tags_embeddings = t_model.encode(train_df['tags'].tolist())
    dev_title_embeddings = t_model.encode(val_df['title'].tolist())
    dev_tags_embeddings = t_model.encode(val_df['tags'].tolist())
    test_title_embeddings = t_model.encode(test_df['title'].tolist())
    test_tags_embeddings = t_model.encode(test_df['tags'].tolist())

    # Concatenate features for train
    X_numerical_train = train_df[NUMERICAL_FEATURES].values
    X_categorical_train = encoded_categorical_train_df.values
    X_title_train = np.array(train_title_embeddings)
    X_tags_train = np.array(train_tags_embeddings)
    X_train = np.concatenate((X_numerical_train, X_categorical_train, X_title_train, X_tags_train), axis=1)

    # Concatenate features for dev
    X_numerical_val = val_df[NUMERICAL_FEATURES].values
    X_categorical_val = encoded_categorical_dev_df.values
    X_title_val = np.array(dev_title_embeddings)
    X_tags_val = np.array(dev_tags_embeddings)
    X_val = np.concatenate((X_numerical_val, X_categorical_val, X_title_val, X_tags_val), axis=1)

    # Concatenate features for test
    X_numerical_test = test_df[NUMERICAL_FEATURES].values
    X_categorical_test = encoded_categorical_test_df.values
    X_title_test = np.array(test_title_embeddings)
    X_tags_test = np.array(test_tags_embeddings)
    X_test = np.concatenate((X_numerical_test, X_categorical_test, X_title_test, X_tags_test), axis=1)

    # Target variables
    y_train = train_df[OUTPUTS].values
    y_val = val_df[OUTPUTS].values
    y_test = test_df[OUTPUTS].values

    return X_train, y_train, X_val, y_val, X_test, y_test

def get_sentence_embedding_model(output_dir):
    """Loads a Sentence Transformer model if it exists, otherwise creates and saves it."""
    model_path = os.path.join(output_dir, 'sentence_transformer_model')

    if os.path.exists(model_path):
        print("Loading existing Sentence Transformer model...")
        t_model = SentenceTransformer(model_path)
    else:
        print("Creating and saving new Sentence Transformer model...")
        t_model = SentenceTransformer('all-MiniLM-L6-v2')
        t_model.save(model_path)
    return t_model

def batchify_data(x_data, y_due, batch_size):
    """Takes a set of data points and labels and groups them into batches."""
    # Only take batch_size chunks (i.e. drop the remainder)
    N = int(len(x_data) / batch_size) * batch_size
    batches = []
    for i in range(0, N, batch_size):
        batches.append({
            'x': torch.tensor(x_data[i:i + batch_size], dtype=torch.float32),
            'y_due': torch.tensor(y_due[i:i + batch_size], dtype=torch.float32)
            })
    return batches

def compute_accuracy_due(pred, target):
    pred = torch.sigmoid(pred) > 0.5
    target = target.bool()
    return (pred == target).float().mean().item()