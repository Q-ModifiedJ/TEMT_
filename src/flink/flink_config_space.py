from openbox import sp
from src.util.config_generator import FlinkConfigGenerator

flink_conf = FlinkConfigGenerator()


def get_flink_1_13_6_config_space():
    """

    :return: A search space consisting of 24 Flink configuration parameters.
    """
    space = sp.Space()
    # slots configuration
    space.add_variables([sp.Int('taskmanager_numberOfTaskSlots', 1, 32, default_value=2)])  # 8

    # memory configuration
    space.add_variables([sp.Int('taskmanager_memory_process_size', 1024, 60000, default_value=1024)])  # 8192M
    space.add_variables([sp.Int('jobmanager_memory_process_size', 1024, 64000, default_value=1024)])  # 8192M

    space.add_variables([sp.Int('jobmanager_memory_jvm-overhead_fraction', 5, 20, default_value=10)])  # 0.05 - 0.20
    space.add_variables([sp.Int('taskmanager_memory_jvm-overhead_fraction', 5, 20, default_value=10)])  # 0.05 - 0.20
    space.add_variables([sp.Int('execution_buffer-timeout', 0, 1000, default_value=100)])  # 100 ms

    space.add_variables([sp.Int('taskmanager_memory_segment-size', 5, 12, default_value=5)])  # 32(2^5) - 4096(2^12)

    space.add_variables([sp.Int('tm_runtime_sort_spilling_threshold', 6, 9, default_value=8)])  # 0.60 - 0.90
    space.add_variables(
        [sp.Int('taskmanager_network_sort-shuffle_min-buffers', 6, 10, default_value=6)])  # 64(2^6) - 1024(2^10)

    space.add_variables([sp.Int('taskmanager_memory_network_fraction', 5, 50, default_value=10)])  # 0.05 - 0.50
    space.add_variables([sp.Int('taskmanager_memory_network_max', 1024, 10240, default_value=1024)])  # 1024 - 10240M
    # 10
    space.add_variables([sp.Int('taskmanager_memory_managed_fraction', 30, 75, default_value=40)])  # 0.30 - 0.75
    space.add_variables([sp.Int('taskmanager_runtime_max-fan', 100, 200, default_value=128)])  # 100 - 200

    # akka
    space.add_variables([sp.Int('akka_framesize', 6, 20, default_value=10)])  # 6 - 20
    space.add_variables([sp.Int('akka_throughput', 5, 40, default_value=15)])  # 5 - 40

    # Netty
    space.add_variables(
        [sp.Int('tm_net_sendReceiveBufferSize', 763659, 8388608, default_value=1048576)])  # 763659 - 1048576
    space.add_variables([sp.Int('tm_net_netty_client_numThreads', 1, 16, default_value=8)])  # 1 - 16
    space.add_variables([sp.Int('tm_net_netty_num-arenas', 1, 8, default_value=8)])  # 1 - 16
    space.add_variables([sp.Int('tm_net_netty_server_numThreads', 1, 16, default_value=8)])  # 1 - 16

    # JVM
    space.add_variables([sp.Int('-XX:NewRatio', 1, 10, default_value=3)])  # 1 - 10
    space.add_variables([sp.Int('-XX:ParallelGCThreads', 1, 4, default_value=4)])  # 1 - 4
    space.add_variables([sp.Int('-XX:GCTimeRatio', 1, 100, default_value=99)])  # 1 - 100

    # Checkpoint Interval and additional parameters
    space.add_variables(
        [sp.Int('execution_checkpointing_interval', 10000, 300000, default_value=180000)])  # 10000 - 300000
    space.add_variables(
        [sp.Int('taskmanager_network_memory_floating-buffers-per-gate', 4, 90, default_value=8)])  # 4 - 90
    return space


def get_extended_flink_1_13_6_config_space():
    """

    :return: A search space consisting of 39 Flink configuration parameters
    """
    space = get_flink_1_13_6_config_space()

    space.add_variables([sp.Int('taskmanager_runtime_hashjoin-bloom-filters', 0, 1, default_value=0)])  # false, true

    space.add_variables([sp.Int('taskmanager_memory_network_min', 64, 1024, default_value=64)])  # 64 - 1024
    space.add_variables([sp.Int('blob_fetch_num-concurrent', 40, 100, default_value=50)])  # 40 - 100
    space.add_variables([sp.Int('blob_fetch_retries', 1, 20, default_value=5)])  # 1 - 20
    space.add_variables([sp.Int('blob_fetch_backlog', 500, 2000, default_value=1000)])  # 500 - 2000

    space.add_variables(
        [sp.Int('blob_offload_minsize', 1048576 // 2, 1048576 * 2, default_value=1048576)])  # 512 - 2048 KB

    space.add_variables([sp.Int('fs_overwrite-files', 0, 1, default_value=0)])  # false, true

    space.add_variables([sp.Int('fs_output_always-create-directory', 0, 1, default_value=0)])  # false, true

    space.add_variables(
        [sp.Int('taskmanager_network_blocking-shuffle_compression_enabled', 0, 1, default_value=0)])  # false, true

    space.add_variables([sp.Int('taskmanager_network_memory_buffers-per-channel', 1, 10, default_value=2)])  # 1 - 10
    space.add_variables(
        [sp.Int('taskmanager_network_memory_max-buffers-per-channel', 10, 100, default_value=10)])  # 10 - 100

    space.add_variables([sp.Int('state.backend.rocksdb.block.blocksize', 4, 256, default_value=4)])  # 4 - 256 KB
    space.add_variables([sp.Int('state.backend.rocksdb.block.cache-size', 8, 256, default_value=8)])  # 8 - 256 MB
    space.add_variables([sp.Int('state.backend.rocksdb.memory.write-buffer-ratio', 2, 8, default_value=5)])  # 0.2-0.8
    space.add_variables([sp.Int('state.backend.rocksdb.thread.num', 1, 32, default_value=4)])  # 1 - 32

    return space


booleanTable = ['false', 'true']


def update_flink_1_13_6_conf_dict(config: sp.Configuration):
    '''
    update configuration parameters (in a dict stored in memory)
    '''

    params = config.get_dictionary()

    flink_conf.add('taskmanager.numberOfTaskSlots', str(params['taskmanager_numberOfTaskSlots']))

    flink_conf.add('taskmanager.memory.process.size', str(params['taskmanager_memory_process_size']) + 'm')
    flink_conf.add('jobmanager.memory.process.size', str(params['jobmanager_memory_process_size']) + 'm')

    flink_conf.add('jobmanager.memory.jvm-overhead.fraction',
                   str(params['jobmanager_memory_jvm-overhead_fraction'] / 100))
    flink_conf.add('taskmanager.memory.jvm-overhead.fraction',
                   str(params['taskmanager_memory_jvm-overhead_fraction'] / 100))
    flink_conf.add('execution.buffer-timeout', str(params['execution_buffer-timeout']) + ' ms')

    flink_conf.add('taskmanager.memory.segment-size', str(2 ** params['taskmanager_memory_segment-size']) + ' kb')

    flink_conf.add('taskmanager.runtime.sort-spilling-threshold',
                   str(params['tm_runtime_sort_spilling_threshold'] / 10))

    flink_conf.add('taskmanager.memory.network.max', str(params["taskmanager_memory_network_max"]) + ' mb')
    flink_conf.add('taskmanager.network.sort-shuffle.min-buffers', str(2 ** params['taskmanager_memory_segment-size']))
    flink_conf.add('taskmanager.memory.network.fraction', str(params['taskmanager_memory_network_fraction'] / 100))
    flink_conf.add('taskmanager.memory.managed.fraction', str(params['taskmanager_memory_managed_fraction'] / 100))

    flink_conf.add('taskmanager.runtime.max-fan', str(params['taskmanager_runtime_max-fan']))

    # akka
    flink_conf.add('akka.framesize', str(params['akka_framesize']) + 'M')
    flink_conf.add('akka.throughput', str(params['akka_throughput']))

    # netty
    flink_conf.add('taskmanager.network.netty.sendReceiveBufferSize', str(params['tm_net_sendReceiveBufferSize']))
    flink_conf.add('taskmanager.network.netty.client.numThreads', str(params['tm_net_netty_client_numThreads']))
    flink_conf.add('taskmanager.network.netty.num-arenas', str(params['tm_net_netty_num-arenas']))
    flink_conf.add('taskmanager.network.netty.server.numThreads', str(params['tm_net_netty_server_numThreads']))

    try:
        # Checkpoint Interval and additional parameters added in 20230602
        flink_conf.add('execution.checkpointing.interval', str(params['execution_checkpointing_interval']) + 'ms')
        flink_conf.add('taskmanager_network_memory_floating-buffers-per-gate',
                       str(params['taskmanager_network_memory_floating-buffers-per-gate']))
    except Exception as e:
        print(e)

    # for env.java.opts:
    try:
        jvm_table = ['-verbose:gc']
        jvm_table.append('-XX:NewRatio=' + str(params['-XX:NewRatio']))
        jvm_table.append('-XX:ParallelGCThreads=' + str(params['-XX:ParallelGCThreads']))
        jvm_table.append('-XX:GCTimeRatio=' + str(params['-XX:GCTimeRatio']))
        flink_conf.add('env.java.opts', ' '.join(jvm_table))
    except Exception as e:
        print(e)

    """
    deal with extended space
    """
    try:
        boolean_str = 'true' if params['taskmanager_runtime_hashjoin-bloom-filters'] > 0.5 else 'false'
        flink_conf.add('taskmanager.runtime.hashjoin-bloom-filters', boolean_str)

        flink_conf.add('taskmanager.memory.network.min', str(params['taskmanager_memory_network_min']) + ' mb')
        flink_conf.add('blob.fetch.num-concurrent', str(params['blob_fetch_num-concurrent']))

        flink_conf.add('blob.fetch.retries', str(params['blob_fetch_retries']))
        flink_conf.add('blob.fetch.backlog', str(params['blob_fetch_backlog']))
        flink_conf.add('blob.offload.minsize', str(params['blob_offload_minsize']))

        boolean_str = 'true' if params['fs_overwrite-files'] > 0.5 else 'false'
        flink_conf.add('fs.overwrite-files', boolean_str)

        boolean_str = 'true' if params['fs_output_always-create-directory'] > 0.5 else 'false'
        flink_conf.add('fs.output.always-create-directory', boolean_str)

        boolean_str = 'true' if params['taskmanager_network_blocking-shuffle_compression_enabled'] > 0.5 else 'false'
        flink_conf.add('taskmanager.network.blocking-shuffle.compression.enabled', boolean_str)

        flink_conf.add('taskmanager.network.memory.buffers-per-channel',
                       str(params['taskmanager_network_memory_buffers-per-channel']))
        flink_conf.add('taskmanager.network.memory.max-buffers-per-channel',
                       str(params['taskmanager_network_memory_max-buffers-per-channel']))
    except Exception as e:
        print("None extended parameters")
        print(e)

    try:
        flink_conf.add('state.backend.rocksdb.block.blocksize',
                       str(params['state.backend.rocksdb.block.blocksize']) + 'KB')
        flink_conf.add('state.backend.rocksdb.block.cache-size',
                       str(params['state.backend.rocksdb.block.cache-size']) + 'MB')
        flink_conf.add('state.backend.rocksdb.memory.write-buffer-ratio',
                       str(int(params['state.backend.rocksdb.memory.write-buffer-ratio']) / 10))
        flink_conf.add('state.backend.rocksdb.thread.num', str(params['state.backend.rocksdb.thread.num']))
    except Exception as e:
        print("None rocksdb parameters")
        print(e)

    return flink_conf


def get_flink_1_13_6_config_parallelism_space():
    space = get_flink_1_13_6_config_space()
    space.add_variables([sp.Int('para1', 1, 12, default_value=8)])
    space.add_variables([sp.Int('para2', 1, 12, default_value=8)])
    space.add_variables([sp.Int('para3', 1, 12, default_value=8)])
    space.add_variables([sp.Int('para4', 1, 12, default_value=8)])
    space.add_variables([sp.Int('para5', 1, 12, default_value=8)])
    space.add_variables([sp.Int('para6', 1, 12, default_value=8)])
    space.add_variables([sp.Int('para7', 1, 12, default_value=8)])
    space.add_variables([sp.Int('para8', 1, 12, default_value=8)])
    return space


def update_tasks_parallelism(config: sp.Configuration):
    params = config.get_dictionary()
    tasks_parallelism = [params['para1'], params['para2'], params['para3'], params['para4'], params['para5'],
                         params['para6'], params['para7'], params['para8']]
    return tasks_parallelism
