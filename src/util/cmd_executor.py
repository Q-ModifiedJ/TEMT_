import os
from abc import ABCMeta, abstractmethod
import paramiko


class BaseAbstractExecutor(metaclass=ABCMeta):
    def __init__(self):
        pass

    @abstractmethod
    def execute(self, cmd: str):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    def putenv(self, name, value):
        pass

    # TODO: Add non-blocking execution method, perhaps using `--nohup`.


# Execute commands on a remote machine
class RemoteExecutor(BaseAbstractExecutor):
    def __init__(self,
                 hostname,
                 username,
                 password=None,
                 port=22,
                 timeout=5,
                 max_retry=3):
        super().__init__()
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # Add to trusted hosts

        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retry = max_retry

    def create(self):
        for i in range(self.max_retry):
            try:
                print('Try to connect remote server')
                self.ssh.connect(hostname=self.hostname,
                                 username=self.username,
                                 password=self.password,
                                 port=self.port,
                                 timeout=self.timeout)
                print("Succeed")
                break
            except:
                print("Retry")

    def execute(self, cmd: str):
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        return stdin, stdout, stderr

    def close(self):
        self.ssh.close()

    def putenv(self, name, value):
        raise NotImplementedError


# Execute commands locally
class LocalExecutor(BaseAbstractExecutor):
    def __init__(self):
        super().__init__()

    def execute(self, cmd: str):
        os.system(cmd)

    def create(self):
        pass

    def close(self):
        pass

    def putenv(self, name, value):
        os.putenv(name, value)
