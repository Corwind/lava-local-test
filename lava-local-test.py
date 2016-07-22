#!/usr/bin/env python
import sys
import os
import glob
import shutil
import time
import re
import yaml
import json
import csv
import subprocess
import pexpect
import argparse
from uuid import uuid4


class TestDefinition(object):
    """
    Analysis and convert test definition.
    """

    def __init__(self):
        self.test_def = test_path + '/' + test_def
        self.test_path = test_path
        # Read the YAML to create a testdef dict
        with open(self.test_def, 'r') as f:
            self.testdef = yaml.safe_load(f)
        self.parameters = self.parameters()
        self.skip_install = skip_install

    def definition(self):
        with open('%s/testdef.yaml' % self.test_path, 'w') as f:
            f.write(yaml.dump(self.testdef, encoding='utf-8', allow_unicode=True))

    def metadata(self):
        with open('%s/testdef_metadata' % self.test_path, 'w') as f:
            f.write(yaml.dump(self.testdef['metadata'], encoding='utf-8', allow_unicode=True))

    def install(self):
        if 'install' not in self.testdef:
            return
        if self.skip_install:
            return

        install_options = self.testdef['install']
        with open('%s/install.sh' % self.test_path, 'w') as f:
            if self.parameters:
                for line in self.parameters:
                    f.write(line)

            f.write('set -e\n')
            f.write('cd %s\n' % self.test_path)
            f.write('###install deps/steps/git-repos defined in test definition###\n')

            if 'git-repos' in install_options:
                git_repos = self.testdef['install'].get('git-repos', [])
                if git_repos:
                    for repo in git_repos:
                        if 'url' in repo:
                            url = repo['url']
                            if 'branch' in repo and repo['branch'] == 'BRANCH':
                                f.write('git clone -b "$BRANCH" %s\n' % url)
                            else:
                                f.write('git clone %s\n' % url)

            if 'deps' in install_options:
                deps = self.testdef['install'].get('deps', [])
                if deps:
                    # TODO: distro-specific dependencies
                    f.write('lava-install-packages ')
                    for dep in deps:
                        f.write('%s ' % dep)
                    f.write('\n')

            if 'steps' in install_options:
                steps = self.testdef['install'].get('steps', [])
                if steps:
                    for cmd in steps:
                        f.write('%s\n' % cmd)

    def run(self):
        with open('%s/run.sh' % self.test_path, 'a') as f:
            if self.parameters:
                for line in self.parameters:
                    f.write(line)

            f.write('set -e\n')
            f.write('export TESTRUN_ID=%s\n' % self.testdef['metadata']['name'])
            f.write('cd %s\n' % self.test_path)
            f.write('UUID=`cat uuid`\n')
            f.write('echo "<LAVA_SIGNAL_STARTRUN $TESTRUN_ID $UUID>"\n')
            steps = self.testdef['run'].get('steps', [])
            if steps:
                for cmd in steps:
                    if '--cmd' in cmd or '--shell' in cmd:
                        cmd = re.sub(r'\$(\d+)\b', r'\\$\1', cmd)
                    f.write('%s\n' % cmd)
            f.write('echo "<LAVA_SIGNAL_ENDRUN $TESTRUN_ID $UUID>"\n')

    def parameters(self):
        ret_val = ['###default parameters from test definition###\n']

        if 'params' in self.testdef:
            for def_param_name, def_param_value in list(self.testdef['params'].items()):
                # ?'yaml_line'
                if def_param_name is 'yaml_line':
                    continue
                ret_val.append('%s=\'%s\'\n' % (def_param_name, def_param_value))
        elif 'parameters' in self.testdef:
            for def_param_name, def_param_value in list(self.testdef['parameters'].items()):
                if def_param_name is 'yaml_line':
                    continue
                ret_val.append('%s=\'%s\'\n' % (def_param_name, def_param_value))
        else:
            return None

        ret_val.append('######\n')
        return ret_val

    def return_pattern(self):
        if 'parse' in self.testdef:
            return self.testdef['parse']['pattern']
        else:
            return None


class TestSetup(object):
    def __init__(self):
        self.repo_name = repo_name
        self.test_name = test_name
        self.uuid = uuid
        self.test_uuid = test_uuid
        self.lava_path = LAVA_PATH
        self.bin_path = bin_path
        self.test_path = test_path

    def copy_test_repo(self):
        shutil.rmtree(self.test_path, ignore_errors=True)
        shutil.copytree(self.repo_name, self.test_path, symlinks=True)

    def create_dir(self):
        if not os.path.exists(self.test_path):
            os.makedirs(self.test_path)

    def create_test_runner_conf(self):
        with open('%s/lava-test-runner.conf' % self.lava_path, 'w') as f:
            f.write(self.test_path)

    def copy_bin_files(self):
        # TODO: handle distro specific files.
        shutil.rmtree(self.bin_path, ignore_errors=True)
        shutil.copytree('lava_test_shell', self.bin_path, symlinks=True)

    def create_uuid_file(self):
        with open('%s/uuid' % self.test_path, 'w') as f:
            f.write(self.uuid)


class TestRunner(object):
    def __init__(self):
        self.lava_path = LAVA_PATH
        self.test_uuid = test_uuid
        self.test_timeout = test_timeout
        print('\nAbout to run %s' % self.test_uuid)
        self.child = pexpect.spawn('%s/bin/lava-test-runner %s' % (self.lava_path, self.lava_path))

    def check_output(self):
        if self.test_timeout:
            print('Test timeout: %s' % self.test_timeout)
            test_end = time.time() + self.test_timeout
        while self.child.isalive():
            try:
                self.child.expect('\n')
                print(self.child.before)
            except pexpect.TIMEOUT:
                if self.test_timeout and time.time() > test_end:
                    print('%s test timed out, killing test process.\n' % self.test_uuid)
                    self.child.terminate(force=True)
                    break
                else:
                    continue
            except pexpect.EOF:
                print('%s test finished.\n' % self.test_uuid)
                break


class ResultPaser(object):
    def __init__(self):
        self.result_path = result_path
        # Fix result path with timestamp added by lava-test-runner.
        self.result_path = glob.glob('%s-[0-9]*' % self.result_path)[0]
        # TODO: handle result parser dfined in testdef
        self.pattern = pattern
        self.metrics = []
        self.results = {}
        self.test_uuid = self.result_path.split('/')[-1]
        self.results['test'] = self.test_uuid.split('_')[0]
        self.results['id'] = self.test_uuid.split('_')[1]

    def run(self):
        self.parse_lava_test_case()
        if self.pattern:
            print('Parse pattern: %s' % self.pattern)
            self.parse_pattern()

        self.dict_to_json()
        self.dict_to_csv()
        print('Result files saved to: %s\n' % self.result_path)

    def parse_lava_test_case(self):
        with open('%s/stdout.log' % self.result_path, 'r') as f:
            for line in f:
                if re.match(r'\<LAVA_SIGNAL_TESTCASE TEST_CASE_ID=.*', line):
                    line = line.strip('\n').strip('<>').split(' ')
                    data = {'test_case_id': '',
                            'result': '',
                            'measurement': '',
                            'units': ''}

                    for string in line:
                        parts = string.split('=')
                        if len(parts) == 2:
                            key, value = parts
                            key = key.lower()
                            data[key] = value

                    self.metrics.append(data.copy())

        self.results['metrics'] = self.metrics

    def parse_pattern(self):
        with open('%s/stdout.log' % self.result_path, 'r') as f:
            for line in f:
                data = {}
                m = re.search(r'%s' % self.pattern, line)
                if m:
                    data = m.groupdict()

                    for x in ['measurement', 'units']:
                        if x not in data:
                            data[x] = ''

                    self.metrics.append(data.copy())

        self.results['metrics'] = self.metrics

    def dict_to_json(self):
        with open('%s/results.json' % self.result_path, 'w') as f:
            json.dump(self.results, f, indent=4)

    def dict_to_csv(self):
        with open('%s/results.csv' % self.result_path, 'w') as f:
            fieldnames = ['test_case_id', 'result', 'measurement', 'units']
            writer = csv.DictWriter(f, fieldnames=fieldnames)

            writer.writeheader()
            for metric in self.results['metrics']:
                writer.writerow(metric)

# Parse arguments.
parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', default='/result', dest='LAVA_PATH',
                    help='Specify a directory store test and result files.')
parser.add_argument('-r', '--repo', dest='git_repo',
                    default='https://git.linaro.org/qa/test-definitions.git',
                    help='Specify url of test definitions git repo.')
parser.add_argument('-d', '--test', required=True, dest='test_def',
                    help='''
                    Specify relative path to test deinition full name.
                    Format example: "ubuntu/smoke-tests-basic.yaml"
                    ''')
parser.add_argument('-t', '--timeout', type=int, default=None,
                    dest='test_timeout', help='Specify test timeout')
parser.add_argument('-s', '--skip_install', dest='skip_install',
                    default=False, action='store_true',
                    help='Specify url of test definitions git repo.')

args = parser.parse_args()

# Test Config
LAVA_PATH = args.LAVA_PATH.rstrip('/')
git_repo = args.git_repo
test_def = args.test_def
test_timeout = args.test_timeout
skip_install = args.skip_install

repo_name = os.path.splitext(git_repo.split('/')[-1])[0]
if not os.path.exists(repo_name):
    subprocess.call(['git', 'clone', git_repo])

uuid = str(uuid4())
test_name = os.path.splitext(test_def.split('/')[-1])[0]
test_uuid = test_name + '_' + uuid
bin_path = LAVA_PATH + '/bin'
test_path = LAVA_PATH + '/tests/' + test_uuid
result_path = LAVA_PATH + '/results/' + test_uuid

# Create a hierarchy of directories and generate files needed.
setup = TestSetup()
setup.copy_test_repo()
setup.create_test_runner_conf()
setup.copy_bin_files()
setup.create_uuid_file()

# Convert test definition to the files needed by lava-test-runner.
test_def = TestDefinition()
test_def.definition()
test_def.metadata()
test_def.install()
test_def.run()
pattern = test_def.return_pattern()

# Test run.
test_run = TestRunner()
test_run.check_output()

# Parse test output, save results in json and csv format.
result_parser = ResultPaser()
result_parser.run()
