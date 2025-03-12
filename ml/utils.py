import os
import torch
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler, OneHotEncoder
from sklearn.model_selection import train_test_split
from sentence_transformers import SentenceTransformer

from torchtext.data.utils import get_tokenizer
from torchtext.vocab import build_vocab_from_iterator
import torchtext

# create train/dev/test
def get_data(input_file):
    print(f"PyTorch version: {torch.__version__}")
    print(f"TorchText version: {torchtext.__version__}")

    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file_path = os.path.join(base_dir, 'output', input_file)
    df = pd.read_csv(input_file_path)

    # Numerical features (scaling)
    numerical_features = ['current_date_dow', 'current_date_dom', 'current_date_m', 'current_date_doy', 'reminder_days',
                          'days_until_due', 'due_date_completion_offset']
    scaler = MinMaxScaler()
    df[numerical_features] = scaler.fit_transform(df[numerical_features])

    # Categorical features (one-hot encoding)
    categorical_features = ['status', 'priority', 'recurrence']
    encoder = OneHotEncoder(sparse_output=False)
    encoded_categorical = encoder.fit_transform(df[categorical_features])
    encoded_categorical_df = pd.DataFrame(encoded_categorical,
                                          columns=encoder.get_feature_names_out(categorical_features))
    df = pd.concat([df, encoded_categorical_df], axis=1).drop(categorical_features, axis=1)

    # Textual features (PyTorch Tokenization and Vocab)
    tokenizer = get_tokenizer('basic_english')  # Or another tokenizer

    def yield_tokens(data_iter):
        for text in data_iter:
            yield tokenizer(text)

    # Build vocab for title
    vocab_title = build_vocab_from_iterator(yield_tokens(df['title']), specials=["<unk>"])
    vocab_title.set_default_index(vocab_title["<unk>"])

    # Build vocab for tags
    vocab_tags = build_vocab_from_iterator(yield_tokens(df['tags']), specials=["<unk>"])
    vocab_tags.set_default_index(vocab_tags["<unk>"])

    def text_pipeline_title(text):
        return vocab_title(tokenizer(text))

    def text_pipeline_tags(text):
        return vocab_tags(tokenizer(text))

    title_sequences = [text_pipeline_title(title) for title in df['title']]
    tags_sequences = [text_pipeline_tags(tags) for tags in df['tags']]

    max_len_title = max(len(seq) for seq in title_sequences)
    max_len_tags = max(len(seq) for seq in tags_sequences)

    padded_title_sequences = [seq + [0] * (max_len_title - len(seq)) for seq in title_sequences]
    padded_tags_sequences = [seq + [0] * (max_len_tags - len(seq)) for seq in tags_sequences]

    # Concatenate features
    X_numerical = df[numerical_features].values
    X_categorical = encoded_categorical_df.values
    X_title = np.array(padded_title_sequences)
    X_tags = np.array(padded_tags_sequences)
    X = np.concatenate((X_numerical, X_categorical, X_title, X_tags), axis=1)

    # Target variables
    y = df[['days_to_show_reminder', 'days_until_due', 'due_date_completion_offset']].values

    print(f"NaN values in X: {np.isnan(X).any()}")
    print(f"Inf values in X: {np.isinf(X).any()}")
    print(f"NaN values in y: {np.isnan(y).any()}")
    print(f"Inf values in y: {np.isinf(y).any()}")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)


    # Split into train and dev
    dev_split_index = int(9 * len(X_train) / 10)
    X_dev = X_train[dev_split_index:]
    y_dev = y_train[dev_split_index:]
    X_train = X_train[:dev_split_index]
    y_train = y_train[:dev_split_index]

    permutation = np.random.permutation(len(X_train))
    X_train = X_train[permutation]
    y_train = y_train[permutation]

    return X_train, y_train, X_dev, y_dev, X_test, y_test

def batchify_data(x_data, y_data, batch_size):
    """Takes a set of data points and labels and groups them into batches."""
    # Only take batch_size chunks (i.e. drop the remainder)
    N = int(len(x_data) / batch_size) * batch_size
    batches = []
    for i in range(0, N, batch_size):
        batches.append({
            'x': torch.tensor(x_data[i:i + batch_size], dtype=torch.float32),
            'y': torch.tensor(y_data[i:i + batch_size], dtype=torch.long
                              )})
    return batches

def compute_accuracy(predictions, y):
    """Computes the accuracy of predictions against the gold labels, y."""
    #return np.mean(np.equal(predictions.detach().numpy(), y.detach().numpy()))
    return torch.mean(torch.abs(predictions - y)).item()