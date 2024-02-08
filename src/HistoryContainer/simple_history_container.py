import collections

from src.HistoryContainer.base_history_container import BaseAbstractHistoryContainer
import pickle


class SimpleHistoryContainer(BaseAbstractHistoryContainer):
    def __init__(self, task_description):
        super(SimpleHistoryContainer, self).__init__()
        self.task_description = task_description

        self.data = collections.OrderedDict()
        self.config_count = 0

        self.all_perfs = []
        self.all_configs = []

    def add(self, config, perf, *args, **kwargs):
        if config in self.data:
            print('Repeated configuration detected!')

        self.data[config] = perf
        self.config_count += 1
        self.all_perfs.append(perf)
        self.all_configs.append(config)

    def get_all_perfs(self) -> list:
        return list(self.data.values())

    def get_all_configs(self) -> list:
        return list(self.data.keys())

    def get_train_x(self):
        raise NotImplementedError

    def get_train_y(self):
        raise NotImplementedError

    def plot_convergence(self) -> None:
        raise NotImplementedError

    def dump(self, dump_path: str):
        f = open(dump_path, 'wb')
        pickle.dump(self, f, 0)
        f.close()

    @staticmethod
    def load(load_path: str):
        f = open(load_path, 'rb')
        container = pickle.load(f)
        f.close()
        return container
