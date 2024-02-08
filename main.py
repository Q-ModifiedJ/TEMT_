import os
from src.optimizer.TEMT_optimizer import TEMTOptimizer

from src.benchmark.nexmark import Nexmark
from src.flink.flink_controller import FlinkController
from src.flink.flink_config_space import get_extended_flink_1_13_6_config_space
from src.HistoryContainer.simple_history_container import SimpleHistoryContainer
import pickle
import time
import resources.conf.flink_config as flcf

# the flink controller
flink = FlinkController(flink_path=flcf.flink_path, flink_name=flcf.flink_name, flink_slaves=flcf.flink_slaves)

# benchmark suite
# The total runtime needed for Nexmark benchmarking may vary based on your physical environment.
# Extend it to ensure all Nexmark instances complete if necessary.
nexmark = Nexmark(wait_time=90, bench_time=200)

# multiple jobs running concurrently. Each of the jobs will be executed by an independent Nexmark instance.
jobs = ['q5', 'q8', 'q1', 'q2', 'q3', 'q4', 'q7', 'q9', 'q10', 'q11', 'q12', 'q13', 'q14', 'q15', 'q16', 'q17']

# additional description information about tuning
task_description = ['Cores', ('q5', 50e3), ('q8', 50e3), ('q1', 50e3), ('q2', 50e3), ('q3', 50e3), ('q4', 50e3),
                    ('q7', 50e3), ('q9', 50e3), ('q10', 50e3), ('q11', 50e3), ('q12', 50e3), ('q13', 50e3),
                    ('q14', 50e3), ('q15', 50e3),
                    ('q16', 50e3), ('q17', 50e3), 'Memory (KB)']
constraints = [50e3 * 0.9] * 16

# number of TEMT iterations
iter_num = 200

# an additional history container observations made during the TEMT tuning process.
additional_container = SimpleHistoryContainer(task_description=task_description)

additional_container_dump_file = 'additional_container_TEMT_' + time.strftime(
    "%Y_%m_%d_%H_%M_%S",
    time.localtime())


#
def clear_output():
    print("Warning, Nexmark q10's output file may not be cleared.")
    # If you run Nexmark q10 job for benchmarking, it will generate output files on disk.
    # After multiple rounds of repeated observations, it may fill up the disk space.
    # If you have run q10, follow the format below to delete output files at each round of iterations.
    # If q10 is not included, simply comment out the print above.

    # os.system("rm -rf /home/anonymous/FlinkBenchmark/nexmark_9/data/output")
    # os.system("ssh xxx.xxx.xxx.xxx \"rm -rf /home/anonymous/FlinkBenchmark/nexmark_9/data/output\"")
    # os.system("ssh xxx.xxx.xxx.xxx \"rm -rf /home/anonymous/FlinkBenchmark/nexmark_9/data/output\"")
    pass


def unnormilized_observation_function(config, task_parallelism=None):
    """

    :param config: A global configuration for Flink
    :param task_parallelism: If tasks_parallelism is None, nexmark will take the preset parallelism.
    :return: [CPU cores, throughput of jobs[0], throughput of jobs[1],... ]
    """
    clear_output()
    params = config.get_dictionary()
    if 'taskmanager_numberOfTaskSlots' in params.keys():
        task_parallelism = [int(params['taskmanager_numberOfTaskSlots']) * 3 // len(jobs)] * len(jobs)

    nexmark.set_task_parallelism(task_parallelism)
    print("start to observe")
    results = nexmark.observe(config, jobs)
    objs = [0]
    for result in results:
        if result['cores'] != 0:
            objs[0] = result['cores']
            break
    for result in results:
        objs.append(result['throughput(msgs/s)'])
    # dump additional container
    additional_container.add(config, objs)
    additional_container.dump(additional_container_dump_file)
    return objs


def unnormilized_observation_function_with_memory(config, task_parallelism=None):
    """
        :param config: A global configuration for Flink
        :param task_parallelism: If tasks_parallelism is None, nexmark will take the preset parallelism.
        :return: [Memory usage, throughput of jobs[0], throughput of jobs[1],... ]
        """
    clear_output()
    params = config.get_dictionary()
    if 'taskmanager_numberOfTaskSlots' in params.keys():
        task_parallelism = [int(params['taskmanager_numberOfTaskSlots']) * 3 // len(jobs)] * len(jobs)

    nexmark.set_task_parallelism(task_parallelism)

    results, memory_usage = nexmark.observe_with_memory(config, jobs)
    objs = [0]
    for result in results:
        if result['cores'] != 0:
            objs[0] = result['cores']
            break
    for result in results:
        objs.append(result['throughput(msgs/s)'])
    objs[0] = memory_usage
    # dump additional container
    additional_container.add(config, objs)
    additional_container.dump(additional_container_dump_file)
    return objs


def TEMT():
    print("TEMT start")
    st = time.time()
    opt = TEMTOptimizer(
        config_space=get_extended_flink_1_13_6_config_space(),
        initial_samples=10,
        max_run=200,
        num_constraints=16,
        objective_function=unnormilized_observation_function,
        similar_factor=0.8,
        task_description=task_description,
        tps_constraints=constraints,
        acqf_opt_restarts=8,
        acqf_opt_raw_samples=48,
        constraints_dropout=True,
        use_worst_approximation=True,
        filter_gaussian_scale=0.5,
        filter_dist_threshold=0,
        auto_filter=False,
        tmp_dump=True,
        reserve_strategy="Spearman",
        reserve_spearman_factor=0.2,
        reserved_random_dimensions=20,
        extraction_strategy="Hierarchical",
        extraction_important_strategy="most",
        extraction_important_num_strategy="Fixed",
        extraction_important_num=5,
        fillingin_strategy_factor=0.5
    )
    opt.run()
    history = opt.get_history()
    # store history data
    f = open('TEMT_' + time.strftime("%Y_%m_%d_%H_%M_%S", time.localtime()), 'wb')
    pickle.dump(history, f, 0)
    f.close()

    # ensure that flink cluster has been stopped.
    flink.stop_cluster()
    ed = time.time()
    print("Total Time:", (ed - st) / 60, "mins")


if __name__ == '__main__':
    # Start TEMT tuning phase.
    TEMT()
