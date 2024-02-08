import paramiko


class SSHConnection(object):
    def __init__(self,
                 hostname,
                 username,
                 password=None,
                 port=22,
                 timeout=5,
                 max_retry=3):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.max_retry = max_retry

    def connect(self):
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

    def cmd(self, cmd: str):
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        return stdin, stdout, stderr

    def close(self):
        self.ssh.close()
