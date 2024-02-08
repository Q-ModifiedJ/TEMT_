import torch

from src.HistoryContainer.simple_history_container import SimpleHistoryContainer
import numpy as np


class MTBOHistoryContainer(SimpleHistoryContainer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_all_perfs(self) -> list:
        perfs = list(self.data.values())
        return perfs

    def get_train_y(self):
        return torch.tensor(self.get_all_perfs(), dtype=torch.float64)

    def get_train_obj(self):
        return self.get_train_y()[:, 0]

    def get_train_constraints(self):
        return self.get_train_y()[:, 1:]

    def get_train_x(self):
        configs = self.get_all_configs()
        # Note: the `get_array()` method will return a normalized configuration parameter array.
        return torch.tensor(np.array([config.get_array() for config in configs]), dtype=torch.float64)

    def get_best_config(self):
        best_config = list(self.data.keys())[0]
        for config in self.data.keys():
            if self.data[config] < self.data[best_config]:
                best_config = config
        return best_config

    def get_best_perf(self):
        return self.data[self.get_best_config()]
