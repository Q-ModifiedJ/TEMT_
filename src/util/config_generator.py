import os
import resources.conf.flink_config as flcf
import resources.conf.nexmark_config as nxcf
from copy import deepcopy


class ConfigGenerator:
    """
    The `ConfigGenerator` class is for generating configuration files.

    """

    confDict = {}  # A dict to save the current parameters' key-value pairs.
    confPath = ''  # The absolute path for the configuration file, for example: /root/bin/
    confName = ''  # Name of the configuration file, for example: config.txt
    confSeparate = ''  # Separator between the name of a configuration parameter and its value.

    # Init
    def __init__(self, init_path, init_name, init_dict={}, init_separate=': '):
        self.confDict.update(init_dict)
        self.confPath = init_path
        self.confName = init_name
        self.confSeparate = init_separate

    # Update the value of parameters. Currently, names and values can only be passed separately.
    def add(self, conf, value):
        if isinstance(conf, list):
            for i in range(len(conf)):
                self.confDict[str(conf[i])] = str(value[i])
        else:
            self.confDict[str(conf)] = str(value)

    def __str__(self):
        string = ""
        keys = self.confDict.keys()
        for aKey in keys:
            if isinstance(self.confDict[aKey], dict):  # Nested parameters for one level.
                string = string + "\n" + str(aKey) + self.confSeparate
                for recursiveKey in self.confDict[aKey].keys():
                    string = string + "\n" + "  " + str(recursiveKey) + self.confSeparate + \
                             str(self.confDict[aKey][recursiveKey])
            else:
                string = string + "\n" + str(aKey) + self.confSeparate + str(self.confDict[aKey])  # 单行的
        return string

    # set the path of configuration file
    def setpath(self, path):
        self.confPath = str(path)

    # set the name of the configuration file.
    def setname(self, name):
        self.confName = str(name)

    # generate the configuration file
    def generate(self):
        try:
            conf_file = open(self.confPath + self.confName, "w+")
            conf_file.write(str(self))
        except IOError:
            print('Error: Failed to generate ' + self.confName + ' configuration!')
        else:
            print('Info: Succeed to generate ' + self.confName + ' configuration.')
            conf_file.close()


class FlinkConfigGenerator(ConfigGenerator):
    def __init__(self):
        flink_conf_path = os.path.join(flcf.flink_home, "conf/")
        self.confDict = dict()
        self.confDict.update(flcf.flink_init_configurations)
        self.confPath = flink_conf_path
        self.confName = "flink-conf.yaml"
        self.confSeparate = ": "
        # Do not invoke the constructor of the parent class.


class NexmarkConfigGenerator(ConfigGenerator):
    def __init__(self):
        raise NotImplementedError


class NexmarkSQLConfigGenerator():

    def __init__(self, sql_config_path):
        init_dict = deepcopy(nxcf.sql_client_init_set)
        init_name = r' parallelism'
        init_path = sql_config_path
        init_separate = "="
        self.confDict = dict()
        self.confDict.update(init_dict)
        self.confPath = init_path
        self.confName = init_name
        self.confSeparate = init_separate

    def add(self, conf, value):
        if isinstance(conf, list):
            for i in range(len(conf)):
                self.confDict[str(conf[i])] = value[i]
        else:
            self.confDict[str(conf)] = value

    def __str__(self):
        string = ""
        keys = self.confDict.keys()
        for aKey in keys:
            if isinstance(self.confDict[aKey], dict):
                string = string + str(aKey) + self.confSeparate + "\n"
                for recursiveKey in self.confDict[aKey].keys():
                    string = string + "\n" + "  " + str(recursiveKey) + self.confSeparate + \
                             str(self.confDict[aKey][recursiveKey]) + "\n"
            else:
                string = string + str(aKey) + self.confSeparate + str(self.confDict[aKey]) + "\n"  # 单行的
        return string

    def setpath(self, path):
        self.confPath = str(path)

    def setname(self, name):
        self.confName = str(name)

    def generate(self):
        try:
            conf_file = open(self.confPath + self.confName, "w+")
            conf_file.write(str(self))
        except IOError:
            print('Error: Failed to generate ' + self.confName + ' configuration!')
        else:
            print('Info: Succeed to generate ' + self.confName + ' configuration.')
            conf_file.close()


# Deprecated
'''
class HiBenchFlinkConfigGenerator(ConfigGenerator):
    def __init__(self):        
        self.confDict = cf.hibench_init_configurations
        self.confPath = cf.hibench_path + 'conf/'
        self.confName = 'flink.conf'
        self.confSeparate = ' '
'''
