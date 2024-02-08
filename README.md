# TEMT


## Introduction
TEMT is an efficient configuration tuning approach for Data Stream Processing Systems (DSPSs). It is specially designed to
handle multiple-job tuning scenario.

## Content
The following directories are included.

- **src**: The source code of TEMT

- **Nexmark**: To demonstrate TEMT's efficiency for handling multiple-job tuning scenario, we simply modified Nexmark benchmark suite to support multiple jobs. 

- **resources**: Some configuration files for TEMT.

- **main.py**: An entrypoint to start the tuning demonstration. Make sure all configuration files are set properly before starting.


## TEMT Requirements
- **Python 3.9.13** or higher is needed. We provide a `requirements.txt` to help you set up the environment. Install all pkts needed by `pip install -r ./requirements.txt`. We recommend you to create a new python environment using Anaconda.

- **JDK 11.0.x** or higher is required.
```
apt install openjdk-11-jdk-headless
```

- Add **passwordless `sudo`** privilege for the current user.

- Make sure you have **passwordless `ssh`** privilege to all the cluster nodes. For each node, nopassword `ssh` is required both to local host and to all remote hosts.

## TEMT Demonstration
To demonstrate TEMT's capability of tuning multiple DSPS's jobs, follow steps below to set up the test environment for Apache Flink on Ubuntu 20.04 servers. 

### Configure Flink standalone clusters
- **Flink standalone 1.13.x** is needed, we recommend to download [Flink 1.13.6](https://archive.apache.org/dist/flink/flink-1.13.6/) and see the [Flink Installation](https://nightlies.apache.org/flink/flink-docs-release-1.13/docs/deployment/resource-providers/standalone/overview/) for how to set up a standalone Flink cluster and [Flink documentation](https://nightlies.apache.org/flink/flink-docs-release-1.13/) for more details.

### Configure Nexmark for multiple-job benchmark
1. See [Nexmark Guidance](Nexmark/README.md) to learn how to build `nexmark-flink.tgz` and configure Nexmark.

2. To support multiple-job benchmark, extract `nexmark-flink.tgz` and make multiple copies of the extracted Nexmark instance according to the number of concurrent jobs you want to test.
```
tar xzf nexmark-flink.tgz
for i in `seq 16`; do cp -r nexmark-flink nexmark_$i; done
```
The above example creates 16 instances of Nexmark, with each copy responsible for benchmarking one job. This example allows for benchmarking up to 16 jobs concurrently.

3. Configure `nexmark_i/conf/nexmark.yaml` for each Nexmark instance `nexmark_i`. 

- : Set `nexmark.metric.reporter.host` to your master IP address.
- : Set `nexmark.metric.reporter.port`. Each Nexmark instance requires a different port.
- : Set `nexmark.metric.monitor.delay`. To avoid incorrect JobID assignments when benchmarking multiple jobs, we start Nexmark instances and submit jobs at a fixed time interval, which is a parameter configurable in TEMT. Based on this interval, corresponding adjustments need to be made to the `nexmark.metric.reporter.delay` within each Nexmark instance.
For example, with a 10-second interval, the `nexmark.metric.reporter.delay` needs to differ by 10 seconds to ensure the metric reporters start simultaneously.
```
nexmark_1/conf/nexmark.yaml
nexmark.metric.reporter.delay: 180s

nexmark_2/conf/nexmark.yaml
nexmark.metrci.reporter.delay: 170s
```

- : Set `nexmark.workload.suite.10m.tps` and `nexmark.workload.suite.datagen.tps` to the input data rate.
- : Set `flink.rest.address` and `flink.rest.port` to your Flink cluster's restful API address and port.


4. Copy all Nexmark instances to your worker nodes using `scp`.


### Configure Tuning settings
- The TEMT tuning process should be deployed on the master node of your Flink cluster. The following three config files need to be configured based on the descriptions provided with in each file.
1. `TEMT/resources/conf/flink_config.py`.
2. `TEMT/resources/conf/nexmark_config.py`.
3. `TEMT/tuner_config.py`.

- We provide a predefined configuration search space for Apache Flink by `get_extended_flink_1_13_6_config_space` in `TEMT/src/flink_config_space.py`. Modify it if you wish to add additional tuning parameters or change the ranges.


### Start Tuning

- We provide TEMT as an individual optimizer in `src/optimizer/TEMT_optimizer.py`, and the entry point for TEMT tuning in `main.py`. Configure the jobs you want to tune concurrently `jobs=[q1, q2,...]` along with their corresponding SLA constraints `constraints = [50000, 50000, ...]`.

- Run `python main.py` to start tht TMET tuning process.

- All history data will be saved as a serialized HistoryContainer object. Use `pickle` to load history container and see the tuning results.


## Transfer TEMT to other data stream processing systems
With some adjustments to tuning settings, TEMT can be transferred to other data stream processing systems.
1. Define a new parameter search space based on the target data stream processing system. Refer to the implementation in `src/flink/flink_config_space.py`.
2. Define a new observation function. It should return a list of `[Target Resource Usage, Constraint Value 1, Constarint Value 2, ..., Constraint Value k]` for totally `k` concurrent jobs.
3. Define the constraints threshold for jobs, and configure the TEMT optimizer.

```
from src.optimizer.TEMT_optimizer.py import TEMTOptimizer

opt = TEMTOptimizer(
        config_space=new_search_space,
        objective_function=new_observation_function,
        tps_constraints=new_constraints,
        *args,
        **kwargs
    )

opt.run()
```


