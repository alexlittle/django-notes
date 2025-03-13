import os
import torch
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer

NUMERICAL_FEATURES = ['current_date_dow', 'current_date_dom', 'current_date_m', 'current_date_doy', 'reminder_days']
CATEGORICAL_FEATURES = ['status', 'priority', 'recurrence']

# create train/dev/test
def get_data(input_file):

    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'output')
    df = pd.read_csv(os.path.join(output_dir, input_file))

    # Numerical features (scaling)
    scaler = MinMaxScaler()
    df[NUMERICAL_FEATURES] = scaler.fit_transform(df[NUMERICAL_FEATURES])
    joblib.dump(scaler, os.path.join(output_dir,'minmax_scaler.joblib'))

    # Categorical features (one-hot encoding)
    encoder = OneHotEncoder(sparse_output=False)
    encoded_categorical = encoder.fit_transform(df[CATEGORICAL_FEATURES])
    encoded_categorical_df = pd.DataFrame(encoded_categorical,
                                          columns=encoder.get_feature_names_out(CATEGORICAL_FEATURES))
    df = pd.concat([df, encoded_categorical_df], axis=1).drop(CATEGORICAL_FEATURES, axis=1)
    joblib.dump(encoder, os.path.join(output_dir,'cat_encoder.joblib'))

    unique_task_ids = df["id"].unique()
    train_ids, test_ids = train_test_split(unique_task_ids, test_size=0.2, random_state=42)
    test_df = df[df["id"].isin(test_ids)]

    train_ids, dev_ids = train_test_split(train_ids, test_size=0.1,  random_state=42)  # 0.1111 is 1/9
    train_df = df[df["id"].isin(train_ids)]
    dev_df = df[df["id"].isin(dev_ids)]

    # Sentence Embeddings
    t_model = get_sentence_embedding_model(output_dir)
    train_title_embeddings = t_model.encode(train_df['title'].tolist())
    train_tags_embeddings = t_model.encode(train_df['tags'].tolist())
    dev_title_embeddings = t_model.encode(dev_df['title'].tolist())
    dev_tags_embeddings = t_model.encode(dev_df['tags'].tolist())
    test_title_embeddings = t_model.encode(test_df['title'].tolist())
    test_tags_embeddings = t_model.encode(test_df['tags'].tolist())

    # One-hot encode 'due'
    due_encoder = OneHotEncoder(sparse_output=False)
    encoded_due_train = due_encoder.fit_transform(train_df[['due']])
    encoded_due_dev = due_encoder.transform(dev_df[['due']])
    encoded_due_test = due_encoder.transform(test_df[['due']])
    joblib.dump(due_encoder, os.path.join(output_dir, 'due_encoder.joblib'))

    # Concatenate features for train
    X_numerical_train = train_df[NUMERICAL_FEATURES].values
    X_categorical_train = encoded_categorical_df.loc[train_df.index].values
    X_title_train = np.array(train_title_embeddings)
    X_tags_train = np.array(train_tags_embeddings)
    X_train = np.concatenate((X_numerical_train, X_categorical_train, X_title_train, X_tags_train), axis=1)

    # Concatenate features for dev
    X_numerical_dev = dev_df[NUMERICAL_FEATURES].values
    X_categorical_dev = encoded_categorical_df.loc[dev_df.index].values
    X_title_dev = np.array(dev_title_embeddings)
    X_tags_dev = np.array(dev_tags_embeddings)
    X_dev = np.concatenate((X_numerical_dev, X_categorical_dev, X_title_dev, X_tags_dev), axis=1)

    # Concatenate features for test
    X_numerical_test = test_df[NUMERICAL_FEATURES].values
    X_categorical_test = encoded_categorical_df.loc[test_df.index].values
    X_title_test = np.array(test_title_embeddings)
    X_tags_test = np.array(test_tags_embeddings)
    X_test = np.concatenate((X_numerical_test, X_categorical_test, X_title_test, X_tags_test), axis=1)

    # Target variables
    y_due_train = encoded_due_train
    y_show_reminder_train = train_df[['show_reminder']].values.astype(np.float32)
    y_due_dev = encoded_due_dev
    y_show_reminder_dev = dev_df[['show_reminder']].values.astype(np.float32)
    y_due_test = encoded_due_test
    y_show_reminder_test = test_df[['show_reminder']].values.astype(np.float32)

    return X_train, y_due_train, y_show_reminder_train, X_test, y_due_test, y_show_reminder_test, X_dev, y_due_dev, y_show_reminder_dev

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

def batchify_data(x_data, y_due, y_show_reminder, batch_size):
    """Takes a set of data points and labels and groups them into batches."""
    # Only take batch_size chunks (i.e. drop the remainder)
    N = int(len(x_data) / batch_size) * batch_size
    batches = []
    for i in range(0, N, batch_size):
        batches.append({
            'x': torch.tensor(x_data[i:i + batch_size], dtype=torch.float32),
            'y_due': torch.tensor(y_due[i:i + batch_size], dtype=torch.float32),  # y_due is one hot encoded, so float.
            'y_show_reminder': torch.tensor(y_show_reminder[i:i + batch_size], dtype=torch.float32) # show_reminder is binary, so float.
            })
    return batches

def compute_accuracy(predictions, y):
    """Computes the accuracy of predictions against the gold labels, y."""
    #return np.mean(np.equal(predictions.detach().numpy(), y.detach().numpy()))
    return torch.mean(torch.abs(predictions - y)).item()

def compute_accuracy_show_reminder(pred, target):
    pred = torch.sigmoid(pred) > 0.5
    target = target.bool()
    return (pred == target).float().mean().item()

def compute_accuracy_due(pred, target):
    pred_classes = torch.argmax(pred, dim=1)
    target_classes = torch.argmax(target, dim=1)
    return (pred_classes == target_classes).float().mean().item()