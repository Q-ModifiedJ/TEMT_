# Flink configuration

"""
flink_home: The full absolute path of your Flink installation.
flink_name: The name of the Flink's directory.
flink_path: flink_home = flink_path +'/' + flink_home

"""
# Assuming your Flink installation is located in /home/anonymous/Flink/flink-1.13.6
flink_path = '/home/anonymous/Flink'
flink_name = 'flink-1.13.6'
flink_home = '/home/anonymous/Flink/flink-1.13.6'

"""
The ip address of your flink workers.
"""
flink_slaves = ['xxx.xxx.xxx.xxx', 'xxx.xxx.xxx.xxx', 'xxx.xxx.xxx.xxx']

"""
These following 5 parameters do no need to be set.
"""
flink_remote_mode = False
remote_hostname = ''
remote_port = ''
remote_password = ''
remote_username = ''

"""
The initial configuration for Flink. It is used to generate Flink configuration in each round of TEMT tuning.
Most of these parameters will be overridden by the default settings provided in TEMT/src/flink/flink_config_space.py, 
but note that the following 4 parameters must be configured properly:

jobmanager.rpc.address: your jobmanager's ip address
io.tmp.dirs
state.checkpoints.dir
state.backend.rocksdb.localdir

"""
flink_init_configurations = {'taskmanager.memory.process.size': '40000M',
                             'jobmanager.rpc.address': 'xxx.xxx.xxx.xxx',
                             'jobmanager.rpc.port': '6123',
                             'jobmanager.memory.process.size': '2048M',
                             'taskmanager.numberOfTaskSlots': '32',
                             'parallelism.default': '8',
                             'io.tmp.dirs': '/mnt/data-ssd/anonymous/tmp',

                             # Job schedule & failover
                             'restart-strategy': 'fixed-delay',
                             'restart-strategy.fixed-delay.attempts': '2147483647',
                             'restart-strategy.fixed-delay.delay': '10 s',
                             'jobmanager.execution.attempts-history-size': '100',

                             # Resources & Slots
                             'slotmanager.taskmanager-timeout': '600000',  # ms

                             # Network
                             'taskmanager.network.memory.floating-buffers-per-gate': '256',
                             'taskmanager.network.memory.buffers-per-external-blocking-channel': '16',
                             'task.external.shuffle.max-concurrent-requests': '512',
                             'task.external.shuffle.compression.enable': 'true',
                             'taskmanager.network.request-backoff.max': '300000',

                             # State & Checkpoint

                             'state.backend': 'rocksdb',
                             'state.checkpoints.dir': 'file:///mnt/data-ssd/anonymous/checkpoint',
                             'state.backend.rocksdb.localdir': '/mnt/data-ssd/anonymous/rocksdb',
                             'state.backend.incremental': 'true',
                             'execution.checkpointing.interval': '500000',
                             'execution.checkpointing.mode': 'EXACTLY_ONCE',
                             'state.backend.local-recovery': 'true',

                             # Runtime Others
                             'akka.ask.timeout': '120 s',
                             'akka.watch.heartbeat.interval': '10 s',
                             'akka.framesize': '102400kB',
                             'web.timeout': '120000',
                             'classloader.resolve-order': 'parent-first',
                             'execution.buffer-timeout': '100 ms',
                             'metrics.latency.interval': '1000',

                             # Additional

                             # 'rest.flamegraph.enabled': 'true',
                             'state.backend.rocksdb.block.blocksize': '126KB',
                             'state.backend.rocksdb.block.cache-size': '255MB',
                             'state.backend.rocksdb.memory.write-buffer-ratio': '0.5',
                             'state.backend.rocksdb.thread.num': '32',
                             # 'state.backend.rocksdb.compaction.level.target-file-size-base': '128MB',
                             # 'state.backend.rocksdb.compaction.level.max-size-level-base': '512MB'

                             }
