# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import io

from badwolf.spec import Specification


def test_parse_empty_conf():
    spec = Specification.parse({})
    assert len(spec.scripts) == 0
    assert len(spec.services) == 0
    assert len(spec.after_success) == 0
    assert len(spec.after_failure) == 0
    assert len(spec.branch) == 0
    assert spec.dockerfile == 'Dockerfile'
    assert len(spec.notification.emails) == 0


def test_parse_single_string_conf():
    spec = Specification.parse({
        'service': 'redis-server',
        'script': 'ls',
        'after_success': 'pwd',
        'after_failure': 'exit',
        'notification': {
            'email': 'messense@icloud.com',
        }
    })
    assert spec.services == ['redis-server']
    assert spec.scripts == ['ls']
    assert spec.after_success == ['pwd']
    assert spec.after_failure == ['exit']
    assert spec.notification.emails == ['messense@icloud.com']


def test_parse_file_single_string():
    s = """script: ls
dockerfile: MyDockerfile
service: redis-server
after_success: pwd
after_failure: exit
notification:
  email: messense@icloud.com"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert spec.dockerfile == 'MyDockerfile'
    assert spec.services == ['redis-server']
    assert spec.scripts == ['ls']
    assert spec.after_success == ['pwd']
    assert spec.after_failure == ['exit']
    assert spec.notification.emails == ['messense@icloud.com']


def test_parse_file_single_list():
    s = """script:
  - ls
dockerfile: MyDockerfile
service:
  - redis-server
after_success:
  - pwd
after_failure:
  - exit
notification:
  email:
    - messense@icloud.com"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert spec.dockerfile == 'MyDockerfile'
    assert spec.services == ['redis-server']
    assert spec.scripts == ['ls']
    assert spec.after_success == ['pwd']
    assert spec.after_failure == ['exit']
    assert spec.notification.emails == ['messense@icloud.com']


def test_parse_file_multi_list():
    s = """script:
  - ls
  - ps
dockerfile: MyDockerfile
service:
  - redis-server
  - postgresql
after_success:
  - pwd
  - rm
after_failure:
  - echo
  - exit
notification:
  email:
    - tech@bosondata.com.cn
    - messense@icloud.com"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert spec.dockerfile == 'MyDockerfile'
    assert spec.services == ['redis-server', 'postgresql']
    assert spec.scripts == ['ls', 'ps']
    assert spec.after_success == ['pwd', 'rm']
    assert spec.after_failure == ['echo', 'exit']
    assert spec.notification.emails == ['tech@bosondata.com.cn', 'messense@icloud.com']


def test_parse_env_single_string():
    s = "env: X=1 Y=2  Z=3\n"
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert len(spec.environments) == 1
    env0 = spec.environments[0]
    assert env0['X'] == '1'
    assert env0['Y'] == '2'
    assert env0['Z'] == '3'


def test_parse_env_single_list():
    s = """env:
  - X=1 Y=2  Z=3"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert len(spec.environments) == 1
    env0 = spec.environments[0]
    assert env0['X'] == '1'
    assert env0['Y'] == '2'
    assert env0['Z'] == '3'


def test_parse_env_multi_list():
    s = """env:
  - X=1 Y=2  Z=3
  - X=3 Y=2  Z=1"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert len(spec.environments) == 2
    env0 = spec.environments[0]
    assert env0['X'] == '1'
    assert env0['Y'] == '2'
    assert env0['Z'] == '3'
    env1 = spec.environments[1]
    assert env1['X'] == '3'
    assert env1['Y'] == '2'
    assert env1['Z'] == '1'


def test_parse_simple_linter():
    s = """linter: flake8"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert len(spec.linters) == 1
    linter0 = spec.linters[0]
    assert linter0.name == 'flake8'
    assert linter0.pattern is None


def test_parse_linter_with_pattern():
    s = """linter: {name: "flake8", pattern: "*.py", whatever: 123}"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert len(spec.linters) == 1
    linter0 = spec.linters[0]
    assert linter0.name == 'flake8'
    assert linter0.pattern == '*.py'
    assert linter0.whatever == 123


def test_parse_multi_linters_with_pattern():
    s = """linter:
  - {name: "flake8", pattern: "*.py"}
  - jscs"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert len(spec.linters) == 2
    linter0 = spec.linters[0]
    assert linter0.name == 'flake8'
    assert linter0.pattern == '*.py'
    linter1 = spec.linters[1]
    assert linter1.name == 'jscs'
    assert linter1.pattern is None


def test_parse_linter_with_regex_pattern():
    s = """linter: {name: "flake8", pattern: '.*\.(sls|yml|yaml)$'}"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert len(spec.linters) == 1
    linter0 = spec.linters[0]
    assert linter0.name == 'flake8'
    assert linter0.pattern == '.*\.(sls|yml|yaml)$'


def test_parse_privileged():
    s = """privileged: True"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert spec.privileged

    s = """privileged: no"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert not spec.privileged

    s = """linter: flake8"""
    f = io.StringIO(s)
    spec = Specification.parse_file(f)
    assert not spec.privileged
