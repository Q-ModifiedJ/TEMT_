import os
from abc import ABCMeta, abstractmethod
import src.flink.flink_config_space as flink_config
import resources.conf.flink_config as flcf
from src.util.cmd_executor import RemoteExecutor, LocalExecutor


class AbstractFlinkController(metaclass=ABCMeta):
    """
    Base class for Flink controller

    """


    @abstractmethod
    def start_cluster(self):
        pass

    @abstractmethod
    def stop_cluster(self):
        pass

    @abstractmethod
    def copy_config_to_slave(self):
        pass

    @abstractmethod
    def copy_all_to_slave(self):
        pass

    @abstractmethod
    def update_config(self, config):
        pass

    @abstractmethod
    def restart_cluster(self):
        pass

    def fetch_slaves(self):
        pass


class FlinkController(AbstractFlinkController):
    """
    The `FlinkController` class provides control operations for a Flink cluster, including starting the cluster,
    stopping the cluster and updating global config ...
    """

    def __init__(self,
                 flink_path: str,  # like '/home/amonoyous/flink'
                 flink_name: str,  # like 'flink-1.13.6'
                 flink_slaves: list,  # like ['172.12.32.3']
                 ):
        # Do not add any / or \ in flink_name
        """
        :param flink_path:
        :param flink_name:
        :param flink_slaves:


        """

        self.flink_path = flink_path
        self.flink_name = flink_name
        self.full_path = os.path.join(flink_path, flink_name)
        self.flink_slaves = flink_slaves

        if flcf.flink_remote_mode:
            # Control of the remote Flink JobManager, currently under development and not recommended for use.
            self.executor = RemoteExecutor(hostname=flcf.remote_hostname, username=flcf.remote_username,
                                           password=flcf.remote_username, port=flcf.remote_username)
        else:
            # The tuning process is on the same server as the Flink JobManager.
            self.executor = LocalExecutor()
        self.executor.create()

    def start_cluster(self):
        print('Try to start Flink cluster')
        cmd = self.full_path + '/bin/start-cluster.sh 1>/dev/null 2>&1'
        try:
            self.executor.execute(cmd)
            print('Succeed')
        except:
            print('Failed to start remote Flink cluster!')
            return False
        return True

    def stop_cluster(self):
        print('Try to stop Flink cluster')
        cmd = self.full_path + '/bin/stop-cluster.sh 1>/dev/null 2>&1'
        try:
            self.executor.execute(cmd)
        except:
            print('Failed to stop remote Flink cluster!')
            return False
        print('Succeed')
        return True

    def restart_cluster(self):
        self.stop_cluster()
        self.start_cluster()

    def update_config(self, config):
        if config is not None:
            conf = flink_config.update_flink_1_13_6_conf_dict(config)  # update config dict (in memory)
            conf.generate()  # write to flink-conf.yaml (to disk)
            self.copy_config_to_slave() # copy flink-conf.yaml to remote workers

    # TODO: add a method to auto get slaves
    def fetch_slaves(self) -> list:
        raise NotImplementedError

    def copy_all_to_slave(self):
        for slave in self.flink_slaves:
            cmd = 'scp -r "%s" "%s:%s"' % (self.full_path, slave, self.flink_path)
            try:
                self.executor.execute(cmd)
            except:
                print('Failed to copy Flink to slave "%s"' % slave)
                return False
        return True

    def copy_config_to_slave(self):
        conf_path = os.path.join(self.full_path, "conf/")
        for slave in self.flink_slaves:
            print("Try to copy config to slave ", slave)
            cmd = 'scp -r "%s" "%s:%s"' % (conf_path, slave, self.full_path)
            try:
                self.executor.execute(cmd)
            except:
                print('Failed to copy config to "%s"' % slave)
                return False
        return True
