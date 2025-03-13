import torch
import torch.nn as nn

class FFNN(nn.Module):
    def __init__(self, input_size, num_due_categories):
        super(FFNN, self).__init__()
        self.common_layers = nn.Sequential(
            nn.Linear(input_size, 256),  # reduce from 512
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Linear(256, 128),  # reduce from 256
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3)
        )
        self.show_reminder_output = nn.Linear(128, 1)  # Single neuron for binary
        self.due_output = nn.Linear(128, num_due_categories)  # n neurons for multi-class


    def forward(self, x):
        common_output = self.common_layers(x)
        show_reminder = torch.sigmoid(self.show_reminder_output(common_output))
        due = self.due_output(common_output)
        return show_reminder, due