
from tqdm import tqdm
import os
import numpy as np
import torch
import torch.nn as nn

from utils import get_data, batchify_data, compute_accuracy_due
from ffnn import FFNN


input_file = "tasks.csv"

def train_model(train_data, val_data, model, lr=0.001, n_epochs=200):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-6)

    for epoch in range(1, n_epochs):
        print("-------------\nEpoch {}:\n".format(epoch))

        # Run **training***
        loss_due, accuracy_due = run_epoch(train_data, model.train(), optimizer)
        print('Due: Train loss: {:.6f} | Train accuracy: {:.6f}'.format(loss_due, accuracy_due))
        # Run **validation**
        val_loss_due,  val_acc_due = run_epoch(val_data, model.eval(), optimizer)
        print('Due: Val loss:   {:.6f} | Val accuracy:   {:.6f}'.format(val_loss_due, val_acc_due))
    # Save model
    torch.save(model.state_dict(), os.path.join('output', 'notes_model.pt'))


def run_epoch(data, model, optimizer):
    """Train model for one pass of train data, and return loss, acccuracy"""
    # Gather losses
    losses_due = []
    batch_accuracies_due = []

    # Loss functions
    criterion_due = nn.BCEWithLogitsLoss()

    # If model is in train mode, use optimizer.
    is_training = model.training

    # Iterate through batches
    for batch in tqdm(data):
        # Grab x and y
        x, y_due = batch['x'], (batch['y_due'])

        # Get output predictions
        due_pred = model(x)
        # Compute losses
        loss_due = criterion_due(due_pred, y_due)
        losses_due.append(loss_due.item())


        batch_accuracies_due.append(compute_accuracy_due( due_pred, y_due))

        # If training, do an update.
        if is_training:
            optimizer.zero_grad()
            loss_due.backward()
            optimizer.step()

    # Calculate epoch level scores
    avg_loss_due = np.mean(losses_due)
    avg_accuracy_due = np.mean(batch_accuracies_due)

    return  avg_loss_due, avg_accuracy_due


def main():
    X_train, y_train, X_val, y_val,  X_test, y_test = get_data(input_file)

    # Split dataset into batches
    batch_size = 32  # 32
    train_batches = batchify_data(X_train, y_train, batch_size)
    val_batches = batchify_data(X_val, y_val,  batch_size)
    test_batches = batchify_data(X_test, y_test,  batch_size)

    input_size = X_train.shape[1]
    output_size = y_train.shape[1]

    print("input size: %d" % input_size)
    print("output size: %d" % output_size)
    model = FFNN(input_size, output_size)
    lr = 0.001

    train_model(train_batches, val_batches, model, lr=lr )

    ## Evaluate the model on test data
    avg_loss_due, avg_accuracy_due = run_epoch(test_batches, model.eval(), None)

    print("Due:  Loss on test set:" + str(avg_loss_due) + " Accuracy on test set: " + str(avg_accuracy_due))
    return

if __name__ == '__main__':
    # Specify seed for deterministic behavior, then shuffle. Do not change seed for official submissions to edx
    np.random.seed(12321)  # for reproducibility
    torch.manual_seed(12321)  # for reproducibility
    print(f"PyTorch version: {torch.__version__}")
    main()