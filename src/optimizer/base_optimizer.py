from abc import ABCMeta, abstractmethod


class BaseAbstractOptimizer(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def get_history(self):
        pass
