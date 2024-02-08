"""
Nexmark jobs. No changes needed.
"""
benchmark_task_table = ['q0', 'q1', 'q2', 'q3', 'q4', 'q5', 'q7', 'q8', 'q9', 'q10', 'q11', 'q12', 'q13', 'q14', 'q15',
                        'q16', 'q17', 'q18', 'q19', 'q20', 'q21', 'q22']


"""
Paths of your Nexmark instances to execute multiple-job benchmarking.
benchmark_homes: The absolute paths to your Nexmark instances.

"""
benchmark_home = '/home/anonymous/FlinkBenchmark/nexmark_p_1'
benchmark_path = '/home/anonymous/FlinkBenchmark'
benchmark_name = 'nexmark_p_1'


benchmark_homes = ['/home/anonymous/FlinkBenchmark/nexmark_1', '/home/anonymous/FlinkBenchmark/nexmark_2',
                   '/home/anonymous/FlinkBenchmark/nexmark_3', '/home/anonymous/FlinkBenchmark/nexmark_4',
                   '/home/anonymous/FlinkBenchmark/nexmark_5', '/home/anonymous/FlinkBenchmark/nexmark_6',
                   '/home/anonymous/FlinkBenchmark/nexmark_7', '/home/anonymous/FlinkBenchmark/nexmark_8',
                   '/home/anonymous/FlinkBenchmark/nexmark_9', '/home/anonymous/FlinkBenchmark/nexmark_10',
                   '/home/anonymous/FlinkBenchmark/nexmark_11', '/home/anonymous/FlinkBenchmark/nexmark_12',
                   '/home/anonymous/FlinkBenchmark/nexmark_13', '/home/anonymous/FlinkBenchmark/nexmark_14',
                   '/home/anonymous/FlinkBenchmark/nexmark_15', '/home/anonymous/FlinkBenchmark/nexmark_16']

benchmark_runnable_home = benchmark_home + '/bin'


"""
Specify temporary files to save reports for each Nexmark instance
"""
nexmark_report_path = '/home/anonymous/tuner/just_tests/nexmark.report.tmp'

nexmark_report_paths = ['/home/anonymous/FlinkBenchmark/report/nexmark_1.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_2.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_3.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_4.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_5.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_6.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_7.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_8.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_9.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_10.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_11.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_12.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_13.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_14.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_15.report.tmp',
                        '/home/anonymous/FlinkBenchmark/report/nexmark_16.report.tmp']


"""
java_home: Set to be your own java home.
"""
java_home = '/usr/lib/jvm/java-11-openjdk-amd64'


"""
These following 2 parameters are no need to be set.
"""
nexmark_task_interval = 10

sql_client_init_set = {
    "SET parallelism.default": "8"
}
