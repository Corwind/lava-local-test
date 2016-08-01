LAVA Local Test
+++++++++++++++
lava-local-test is developed for executing LAVA test definitions on local test target. It feeds lava-test-runner with everything it needs and executes it without LAVA instance. lava-test-runner is part of lava-test-shell which is provided by `lava-dispatch <https://git.linaro.org/lava/lava-dispatcher.git>`_ for test automation.

Requirements
============
- Python 2.7
- Linux(Debian or fedora based)

Basic Usage
===========
It uses Linaro `qa/test-definitions <https://git.linaro.org/qa/test-definitions.git>`_ as the default test repo, which can be modified with "-r". It supports remote git repo and local repo as well. Execute "./lava-local-test -h" for detailed help info. Either option "-d test_def" or "-a agenda_file" is required.
        lava-local-test.py [-h] [-o LAVA_PATH] [-a AGENDA] [-r REPO] [-d TEST_DEF] [-t TEST_TIMEOUT] [-s]

Examples
--------
Run a simple smoke test:
        ./lava-local-test.py -d ubuntu/smoke-tests-basic.yaml

Run multiple tests with agenda file. The current agenda schema supports to customize test params, skip install steps and set timeout for each test, refer to `agenda-example.yaml <./agenda-example.yaml>`_:
        ./lava-local-test.py -a agenda-example.yaml

Modify test output directory, the default is ./output:
        ./lava-local-test.py -d ubuntu/smoke-tests-basic.yaml -o /tmp

Specify a different remote git test definition repo:
        ./lava-local-test.py -d ubuntu/smoke-tests-basic.yaml -r https://git.linaro.org/people/chase.qi/test-definitions.git

Use a local test definition repo:
        ./lava-local-test.py -d ubuntu/smoke-tests-basic.yaml -r ./test-definitions

Skip install steps defined in test definition:
        ./lava-local-test.py -d ubuntu/pi-stress-test.yaml -s

Set test timeout to 30 minutes:
        ./lava-local-test.py -d ubuntu/pi-stress-test.yaml -t 1800

Test result files will be saved to ./output/results/test-name_uuid/ in json and csv format.

For multiple test runs with agenda file, ./output/results.csv also will be created to collect test results from all tests.

License
=======
LAVA Local Test is distributed under GPL Version 2.

Feedback and Support
====================
Contact chase.qi@linaro.org
