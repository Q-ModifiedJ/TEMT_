from abc import ABCMeta, abstractmethod


class BaseAbstractBenchmark(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod
    def observe(self, *args, **kwargs):
        pass
