
from tqdm import tqdm
import os
import numpy as np
import torch
import torch.nn as nn

from utils import get_data, batchify_data, compute_accuracy_due, compute_accuracy_show_reminder
from ffnn import FFNN


input_file = "tasks.csv"

def train_model(train_data, dev_data, model, lr=0.001, n_epochs=100):
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(1, n_epochs):
        print("-------------\nEpoch {}:\n".format(epoch))

        # Run **training***
        loss_show_reminder, loss_due, accuracy_show_reminder, accuracy_due = run_epoch(train_data, model.train(), optimizer)
        print('Show Reminder: Train loss: {:.6f} | Train accuracy: {:.6f}'.format(loss_show_reminder, accuracy_show_reminder))
        print('Due: Train loss: {:.6f} | Train accuracy: {:.6f}'.format(loss_due, accuracy_due))
        # Run **validation**
        val_loss_show_reminder, val_loss_due,  val_acc_show_reminder, val_acc_due = run_epoch(dev_data, model.eval(), optimizer)
        print('Show Reminder: Val loss:   {:.6f} | Val accuracy:   {:.6f}'.format(val_loss_show_reminder, val_acc_show_reminder))
        print('Due: Val loss:   {:.6f} | Val accuracy:   {:.6f}'.format(val_loss_due, val_acc_due))
        # Save model
        torch.save(model.state_dict(), os.path.join('output', 'notes_model.pt'))


def run_epoch(data, model, optimizer):
    """Train model for one pass of train data, and return loss, acccuracy"""
    # Gather losses
    losses_show_reminder = []
    losses_due = []
    batch_accuracies_show_reminder = []
    batch_accuracies_due = []

    # Loss functions
    criterion_show_reminder = nn.BCEWithLogitsLoss()
    criterion_due = nn.CrossEntropyLoss()

    # If model is in train mode, use optimizer.
    is_training = model.training

    # Iterate through batches
    for batch in tqdm(data):
        # Grab x and y
        x, (y_due, y_show_reminder) = batch['x'], (batch['y_due'], batch['y_show_reminder'])

        # Get output predictions
        show_reminder_pred, due_pred = model(x)
        # Compute losses
        loss_show_reminder = criterion_show_reminder(show_reminder_pred, y_show_reminder)
        loss_due = criterion_due(due_pred, torch.argmax(y_due, dim=1))  # argmax to get the class index.

        losses_show_reminder.append(loss_show_reminder.item())
        losses_due.append(loss_due.item())

        # Compute accuracies (or other metrics)
        # Note: You'll need to implement or adapt compute_accuracy functions for each branch.
        batch_accuracies_show_reminder.append(compute_accuracy_show_reminder(show_reminder_pred, y_show_reminder))
        batch_accuracies_due.append(compute_accuracy_due(due_pred, y_due))

        # If training, do an update.
        if is_training:
            optimizer.zero_grad()
            total_loss = loss_show_reminder + loss_due
            total_loss.backward()
            optimizer.step()

    # Calculate epoch level scores
    avg_loss_show_reminder = np.mean(losses_show_reminder)
    avg_loss_due = np.mean(losses_due)
    avg_accuracy_show_reminder = np.mean(batch_accuracies_show_reminder)
    avg_accuracy_due = np.mean(batch_accuracies_due)

    return avg_loss_show_reminder, avg_loss_due, avg_accuracy_show_reminder, avg_accuracy_due


def main():
    X_train, y_due_train, y_show_reminder_train, X_test, y_due_test, y_show_reminder_test, X_dev, y_due_dev, y_show_reminder_dev = get_data(input_file)

    # Split dataset into batches
    batch_size = 32  # 32
    train_batches = batchify_data(X_train, y_due_train, y_show_reminder_train, batch_size)
    dev_batches = batchify_data(X_dev, y_due_dev, y_show_reminder_dev, batch_size)
    test_batches = batchify_data(X_test, y_due_test, y_show_reminder_test,  batch_size)

    input_size = X_train.shape[1]
    output_size = y_due_train.shape[1]

    print("input size: %d" % input_size)
    model = FFNN(input_size, output_size)
    lr = 0.001

    train_model(train_batches, dev_batches, model, lr=lr )

    ## Evaluate the model on test data
    avg_loss_show_reminder, avg_loss_due, avg_accuracy_show_reminder, avg_accuracy_due = run_epoch(test_batches, model.eval(), None)

    print("Due:  Loss on test set:" + str(avg_loss_due) + " Accuracy on test set: " + str(avg_accuracy_due))
    print("Show reminder:  Loss on test set:" + str(avg_loss_show_reminder) + " Accuracy on test set: " + str(avg_accuracy_show_reminder))
    return

if __name__ == '__main__':
    # Specify seed for deterministic behavior, then shuffle. Do not change seed for official submissions to edx
    np.random.seed(12321)  # for reproducibility
    torch.manual_seed(12321)  # for reproducibility
    print(f"PyTorch version: {torch.__version__}")
    main()