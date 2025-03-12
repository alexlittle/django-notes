
from tqdm import tqdm
import numpy as np
import torch
import torch.nn.functional as F

from utils import get_data, compute_accuracy, batchify_data
from ffnn import FFNN


input_file = "tasks.csv"

def train_model(train_data, dev_data, model, lr=0.001, n_epochs=1000):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(1, n_epochs):
        print("-------------\nEpoch {}:\n".format(epoch))

        # Run **training***
        loss, acc = run_epoch(train_data, model.train(), optimizer)
        print('Train loss: {:.6f} | Train accuracy: {:.6f}'.format(loss, acc))

        # Run **validation**
        val_loss, val_acc = run_epoch(dev_data, model.eval(), optimizer)
        print('Val loss:   {:.6f} | Val accuracy:   {:.6f}'.format(val_loss, val_acc))
        # Save model
        torch.save(model, 'notes_model.pt')
    return val_acc

def run_epoch(data, model, optimizer):
    """Train model for one pass of train data, and return loss, acccuracy"""
    # Gather losses
    losses = []
    batch_accuracies = []

    # If model is in train mode, use optimizer.
    is_training = model.training

    # Iterate through batches
    for batch in tqdm(data):
        # Grab x and y
        x, y = batch['x'], batch['y']

        # Get output predictions
        out = model(x)

        batch_accuracies.append(compute_accuracy(out, y))

        # Compute loss
        loss = F.mse_loss(out, y.float())
        losses.append(loss.data.item())

        # If training, do an update.
        if is_training:
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

    # Calculate epoch level scores
    avg_loss = np.mean(losses)
    avg_accuracy = np.mean(batch_accuracies)
    return avg_loss, avg_accuracy


def main():
    X_train, y_train, X_test, y_test, X_dev, y_dev = get_data(input_file)

    # Split dataset into batches
    batch_size = 32  # 32
    train_batches = batchify_data(X_train, y_train, batch_size)
    dev_batches = batchify_data(X_dev, y_dev, batch_size)
    test_batches = batchify_data(X_test, y_test, batch_size)

    input_size = X_train.shape[1]
    output_size = y_train.shape[1]

    model = FFNN(input_size, output_size)
    lr = 0.001  # 0.1

    train_model(train_batches, dev_batches, model, lr=lr )

    ## Evaluate the model on test data
    loss, accuracy = run_epoch(test_batches, model.eval(), None)

    print("Loss on test set:" + str(loss) + " Accuracy on test set: " + str(accuracy))
    return

if __name__ == '__main__':
    # Specify seed for deterministic behavior, then shuffle. Do not change seed for official submissions to edx
    np.random.seed(12321)  # for reproducibility
    torch.manual_seed(12321)  # for reproducibility
    main()