from basebenchmark import BaseAbstractBenchmark


# TODO: Add support for HiBench.
class HiBench(BaseAbstractBenchmark):
    def __init__(self):
        super().__init__()
        raise NotImplementedError

    def observe(self, config, tasks: list):
        pass
