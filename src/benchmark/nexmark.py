import os
import resources.conf.nexmark_config as nxcf
import resources.conf.flink_config as flcf
import resources.conf.tuner_config as tncf
from src.flink.flink_controller import FlinkController
from subprocess import Popen
import time
from src.benchmark.basebenchmark import BaseAbstractBenchmark
import warnings
from src.util.config_generator import NexmarkSQLConfigGenerator
from src.util.memory_monitor import MemoryMonitor


"""
Nexmark

The `Nexmark` class provides operations for interacting with the Nexmark benchmark, including submitting multiple test 
jobs, collecting task execution metrics, and observing the candidate configuration provided by TEMT.

"""

class Nexmark(BaseAbstractBenchmark):
    def __init__(self, wait_time, bench_time):
        """

        :param wait_time:
        :param bench_time:
        """
        super().__init__()
        self.flink = FlinkController(flink_path=flcf.flink_path, flink_slaves=flcf.flink_slaves,
                                     flink_name=flcf.flink_name)
        self.wait_time = wait_time
        self.bench_time = bench_time
        self.bench_home = nxcf.benchmark_runnable_home
        self.bench_task_table = nxcf.benchmark_task_table

        os.putenv('FLINK_HOME', flcf.flink_home)
        os.putenv('JAVA_HOME', nxcf.java_home)

        self.task_sql_clients_config = []
        for home in nxcf.benchmark_homes:
            self.task_sql_clients_config.append(NexmarkSQLConfigGenerator(os.path.join(home, 'bin/')))

    def run_benchmark_tasks(self, tasks: list) -> list:
        """

        :param tasks: a list of Nemark workloads to run jointly. e.g. ['q1','q2']
        :return: None
        """
        print("we have", tasks)
        # make sure that all previous Nexmark process are terminated properly
        os.system(os.path.join(tncf.shell_home, 'nexmark_ensure_stop.sh'))
        self.flink.restart_cluster()
        try:
            self.submit_tasks(tasks)
        except Exception as E:
            print("Exception when submit tasks")
            print(E)
        print("Start to Sleep", self.wait_time + self.bench_time, "seconds")
        time.sleep(self.wait_time)

        # If a custom metrics reporter is available, the metric collection should commence at this point

        time.sleep(self.bench_time)
        print("Sleep finish")
        self.flink.stop_cluster()

        results = self.get_metrics(tasks)
        return results

    def run_benchmark_tasks_with_memory_monitor(self, tasks: list):
        """

        :param tasks: a list of Nemark workloads to run jointly. e.g. ['q1','q2']
        :return: None
        """

        print("we have", tasks)
        # make sure that all previous Nexmark process are terminated properly
        os.system(os.path.join(tncf.shell_home, 'nexmark_ensure_stop.sh'))
        self.flink.restart_cluster()
        try:
            self.submit_tasks(tasks)
        except Exception as E:
            print("Exception when submit tasks")
            print(E)
        print("Start to Sleep", self.wait_time + self.bench_time, "seconds")
        time.sleep(30)

        m = MemoryMonitor(bench_time=155, bench_interval=1)
        # a custom memory metrics reporter
        average_memory_usage = m.start()
        time.sleep(30)
        print("Sleep finish")
        self.flink.stop_cluster()

        results = self.get_metrics(tasks)
        return results, average_memory_usage

    def get_metrics(self, tasks: list) -> list:
        """

        :param tasks: a list of Nemark workloads to run jointly. e.g. ['q1','q2']
        :return: a list of dict, includes metrics for each task.
            e.g. [{"Cores":1,"Throughput(msgs/s):10000"},{"Cores":1,"Throughput(msgs/s):20000"}]
        """
        metrics = []
        for n in range(len(tasks)):
            report_path = nxcf.nexmark_report_paths[n]
            metrics.append(self.read_report_file(report_path))
        return metrics

    # TODO: rewrite it
    def read_report_file(self, report_file: str) -> dict:
        """

        :param report_file: Nexmark metrics report file
        :return: a metrics dict. e.g.{"Cores":1,"Throughput(msgs/s):10000"}
        """

        # Extract the 6th line and locate the throughput data and units by identifying the '|' delimiter.
        # TODO: This method seems inefficient; Use RE instead.
        cores = 0
        try:
            with open(report_file, 'r') as f:
                content = f.readlines()
                cores_line = content[5]
                cores_list = cores_line.split('|')[3].split(' ')
                cores = 0
            for i in range(len(cores_list)):
                try:
                    cores_list.remove('')
                except:
                    break
            cores = float(cores_list[0])
        except:
            pass

        try:
            with open(report_file, 'r') as f:
                content = f.readlines()
                tps_line = content[5]
                tps_list = tps_line.split('|')[2].split(' ')

                tps = 0

            for i in range(len(tps_list)):
                try:
                    tps_list.remove('')
                except:
                    break

            if len(tps_list) == 1:
                unit = 'One'
                tps = float(tps_list[0])
            else:
                unit = tps_list[1]
                tps = float(tps_list[0])
        except:
            unit = 'K'
            tps = 0

        if unit == 'K':
            tps *= 1000
        elif unit == 'M':
            tps *= 1000000
        elif unit == 'One':
            pass
        else:
            raise ValueError("The throughput unit is incorrect")
        metrics = {}
        metrics['throughput(msgs/s)'] = tps
        metrics['cores'] = cores
        return metrics

    def submit_tasks(self, tasks: list) -> bool:
        """
        Given a group of tasks, use Nexmark to submit them to Flink cluster.
        :param tasks: a list of tasks. e.g.['q1','q2']
        :return: None
        """
        # nexmark shutdown_clusters.sh
        os.system(os.path.join(nxcf.benchmark_homes[0], "bin/shutdown_cluster.sh"))

        for n in range(len(tasks)):
            # setup all nexmark metrics clusters
            os.system(os.path.join(nxcf.benchmark_homes[n], "bin/setup_cluster.sh"))

        # submit all tasks sequentially
        for n in range(len(tasks)):
            # Ignore warning from Popen: ("subprocess %s is still running")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                # Using `-d` to locate the SQL-Client_SET file path in Nexmark always defaults to the current workling directory.
                # Therefore, navigate to the `bin` directory inside each Nexmark instance before proceeding
                cmd = 'cd "%s";./run_query.sh "%s" 2>"%s"' \
                      % (nxcf.benchmark_homes[n] + '/bin', tasks[n], nxcf.nexmark_report_paths[n])
                Popen(cmd, shell=True, env={'FLINK_HOME': flcf.flink_home})

            print('Nexmark ' + tasks[n] + ' started.')
            time.sleep(nxcf.nexmark_task_interval)  # A time interval to help Nexmark identify each job's jobID

        return True

    def observe(self, config, tasks) -> list:
        """

        :param config: Configuration
        :param tasks: list of tasks, e.g.['q1']
        :return: list of results dict
        """
        assert len(tasks) <= len(nxcf.benchmark_homes), 'Only support "%s" tasks' % len(nxcf.benchmark_homes)
        self.flink.update_config(config)
        results = self.run_benchmark_tasks(tasks=tasks)
        self.clean_cache_files()
        return results

    def observe_with_memory(self, config, tasks):
        """

        :param config: Configuration
        :param tasks: list of tasks, e.g.['q1']
        :return: list of results dict
        """
        assert len(tasks) <= len(nxcf.benchmark_homes), 'Only support "%s" tasks' % len(nxcf.benchmark_homes)
        self.flink.update_config(config)
        results, memory = self.run_benchmark_tasks_with_memory_monitor(tasks=tasks)
        self.clean_cache_files()
        return results, memory

    def set_task_parallelism(self, parallelism=None):
        """

        :param parallelism:
        parallelism for tasks
        [p1, p2, p3, ...]
        :return:
        """
        if parallelism is None:
            parallelism = [12] * len(nxcf.benchmark_homes)
        for i in range(len(parallelism)):
            sql_config_generator = self.task_sql_clients_config[i]
            sql_config_generator.add("SET parallelism.default", str(parallelism[i]))
            sql_config_generator.generate()

    def clean_cache_files(self):

        """
        delete state cache file generated during each round of benchmark
        
        """
        tmp_dir = flcf.flink_init_configurations['io.tmp.dirs']
        ckp_dir = flcf.flink_init_configurations['state.checkpoints.dir'][7:]
        rocksdb_dir = flcf.flink_init_configurations['state.backend.rocksdb.localdir']

        """
        TODO:
        Make sure tmp_dir, ckp_dir and rocksdb_dir is not null!!!!!!!
        
        """
        assert tmp_dir
        assert ckp_dir
        assert rocksdb_dir

        os.system('rm -rf {}/*'.format(tmp_dir))
        os.system('rm -rf {}/*'.format(ckp_dir))
        os.system('rm -rf {}/*'.format(rocksdb_dir))

        """
        delete cache file on remote flink workers
        """
        for taskmanager in flcf.flink_slaves:
            os.system('ssh {} rm -rf {}/*'.format(taskmanager, tmp_dir))
            os.system('ssh {} rm -rf {}/*'.format(taskmanager, ckp_dir))
            os.system('ssh {} rm -rf {}/*'.format(taskmanager, rocksdb_dir))
