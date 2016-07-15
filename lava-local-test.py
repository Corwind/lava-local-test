import sys
import os
import shutil
import time
import re
import yaml
import subprocess
import pexpect
from uuid import uuid4


HOME = os.environ['HOME']
LAVA_PATH = HOME + '/lava_test_output'
test_definition = 'smoke.yaml'


class TestDefinition(object):
    """
    Analysis and convert test definition.
    """

    def __init__(self, test_definition, test_path):
        self.test_definition = test_definition
        self.test_path = test_path
        # Read the YAML to create a testdef dict
        with open(self.test_definition, 'r') as test_file:
            self.testdef = yaml.safe_load(test_file)

    def definition(self):
        with open('%s/testdef.yaml' % self.test_path, 'w') as f:
            f.write(yaml.dump(self.testdef, encoding='utf-8', allow_unicode=True))

    def metadata(self):
        with open('%s/testdef_metadata' % self.test_path, 'w') as f:
            f.write(yaml.dump(self.testdef['metadata'], encoding='utf-8', allow_unicode=True))

    def install(self):
        pass

    def run(self):
        with open('%s/run.sh' % self.test_path, 'a') as runsh:
            runsh.write('set -e\n')
            runsh.write('export TESTRUN_ID=%s\n' % self.testdef['metadata']['name'])
            runsh.write('cd %s\n' % self.test_path)
            runsh.write('UUID=`cat uuid`\n')
            runsh.write('echo "<LAVA_SIGNAL_STARTRUN $TESTRUN_ID $UUID>"\n')
            steps = self.testdef['run'].get('steps', [])
            if steps:
                for cmd in steps:
                    if '--cmd' in cmd or '--shell' in cmd:
                        cmd = re.sub(r'\$(\d+)\b', r'\\$\1', cmd)
                    runsh.write('%s\n' % cmd)
            runsh.write('echo "<LAVA_SIGNAL_ENDRUN $TESTRUN_ID $UUID>"\n')

    def parameters(self):
        pass


class TestSetup(object):
    def __init__(self, lava_path, test_definition):
        self.lava_path = lava_path
        self.test_name = os.path.splitext(test_definition)[0]
        self.uuid = str(uuid4())
        self.test_uuid = self.test_name + '_' + self.uuid
        self.bin_path = lava_path + '/bin'
        self.test_path = lava_path + '/tests/' + self.test_uuid
        self.result_path = lava_path + '/results/' + self.test_uuid

    def create_dir(self):
        if not os.path.exists(self.test_path):
            os.makedirs(self.test_path)

    def create_test_runner_conf(self):
        with open('%s/lava-test-runner.conf' % self.lava_path, 'w') as f:
            f.write(self.test_path)

    def copy_bin_files(self):
        shutil.rmtree(self.bin_path, ignore_errors=True)
        shutil.copytree('lava_test_shell', self.bin_path, symlinks=True)

    def create_uuid_file(self):
        with open('%s/uuid' % self.test_path, 'w') as f:
            f.write(self.uuid)

    def get_test_path(self):
        return self.test_path

    def get_result_path(self):
        return self.result_path


class TestRunner(object):
    def __init__(self, lava_path):
        self.lava_path = lava_path
        self.child = pexpect.spawn('%s/bin/lava-test-runner %s' % (self.lava_path, self.lava_path))

    def check_output(self):
        while True:
            try:
                self.child.expect('\n')
                print(self.child.before)
            except pexpect.EOF:
                break

# Create a hierarchy of directories and files needed.
test_setup = TestSetup(LAVA_PATH, test_definition)
test_setup.create_dir()
test_setup.create_test_runner_conf()
test_setup.copy_bin_files()
test_setup.create_uuid_file()
test_path = test_setup.get_test_path()

# Convert test definition to the files needed by lava-test-runner.
test_def = TestDefinition(test_definition, test_path)
test_def.definition()
test_def.metadata()
test_def.install()
test_def.run()

# Test run.
test_run = TestRunner(LAVA_PATH)
test_run.check_output()
