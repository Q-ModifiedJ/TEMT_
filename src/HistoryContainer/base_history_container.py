from abc import ABCMeta, abstractmethod


class BaseAbstractHistoryContainer(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod
    def get_all_configs(self) -> list:
        """

        :return:
        """
        pass

    @abstractmethod
    def get_all_perfs(self) -> list:
        """

        :return:
        """
        pass

    @abstractmethod
    def get_train_x(self):
        pass

    @abstractmethod
    def get_train_y(self):
        pass

    @abstractmethod
    def plot_convergence(self) -> None:
        """

        :return:
        """
        pass

    @abstractmethod
    def add(self, config, perfs, *args, **kwargs) -> None:
        """

        :param config:
        :param perfs:
        :param args:
        :param kwargs:
        :return:
        """
        pass

    @abstractmethod
    def dump(self, path: str):
        pass

    @staticmethod
    @abstractmethod
    def load(path: str):
        pass
