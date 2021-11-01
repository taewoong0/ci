#!/usr/bin/env python3

# Copyright 2015 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import collections
import copy
import os
import re
import sys

try:
    import ros_buildfarm  # noqa
except ImportError:
    sys.exit("Could not import ros_buildfarm, please add it to the PYTHONPATH.")

try:
    import jenkinsapi  # noqa
except ImportError:
    sys.exit("Could not import jenkinsapi, please install it with pip or apt-get.")

from ros_buildfarm.jenkins import configure_job
from ros_buildfarm.jenkins import connect
from ros_buildfarm.templates import expand_template
try:
    from ros_buildfarm.templates import template_prefix_path
except ImportError:
    sys.exit("Could not import symbol from ros_buildfarm, please update ros_buildfarm.")

DEFAULT_REPOS_URL = 'https://raw.githubusercontent.com/gurumnet/ros2/{ros_distro}/ros2.repos'
DEFAULT_MAIL_RECIPIENTS = 'taewoong@gurum.cc'
PERIODIC_JOB_SPEC = '30 7 * * *'

template_prefix_path[:] = \
    [os.path.join(os.path.abspath(os.path.dirname(__file__)), 'job_templates')]


def nonnegative_int(inval):
    try:
        ret = int(inval)
    except ValueError:
        ret = -1
    if ret < 0:
        raise argparse.ArgumentTypeError('Value must be nonnegative integer')
    return ret

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser(description="Creates the ros2 jobs on Jenkins")
    parser.add_argument(
        '--jenkins-url', '-u', default='https://ci.gurum.cc',
        help="Url of the jenkins server to which the job should be added")
    parser.add_argument(
        '--ci-scripts-repository', default='git@github.com:taewoong0/ci.git',
        help="repository from which ci scripts should be cloned"
    )
    parser.add_argument(
        '--ci-scripts-default-branch', default='master',
        help="default branch of the ci repository to get ci scripts from (this is a job parameter)"
    )
    parser.add_argument(
        '--commit', action='store_true',
        help='Actually modify the Jenkins jobs instead of only doing a dry run',
    )
    parser.add_argument(
        '--select-jobs-regexp', default='',
        help='Limit the job creation to those that match the given regular expression'
    )
    parser.add_argument(
        '--context-lines', type=nonnegative_int, default=0,
        help='Set the number of diff context lines when showing differences between old and new jobs'
    )
    args = parser.parse_args(argv)

    data = {
        'build_discard': {
            'days_to_keep': 1000,
            'num_to_keep': 3000},
        'ci_scripts_repository': args.ci_scripts_repository,
        'ci_scripts_default_branch': args.ci_scripts_default_branch,
        'default_repos_url': '',
        'supplemental_repos_url': '',
        'time_trigger_spec': '',
        'mailer_recipients': '',
        'ignore_rmw_default': {
            'rmw_connext_dynamic_cpp',
            'rmw_fastrtps_dynamic_cpp'},
        'use_isolated_default': 'true',
        'colcon_mixin_url': 'https://raw.githubusercontent.com/colcon/colcon-mixin-repository/master/index.yaml',
        'build_args_default': '--event-handlers console_cohesion+ console_package_list+ --cmake-args -DINSTALL_EXAMPLES=OFF -DSECURITY=ON',
        'test_args_default': '--event-handlers console_direct+ --executor sequential --retest-until-pass 2 --ctest-args -LE xfail --pytest-args -m "not xfail"',
        'compile_with_clang_default': 'false',
        'enable_coverage_default': 'false',
        'dont_notify_every_unstable_build': 'false',
        'build_timeout_mins': 0,
        'ubuntu_distro': 'focal',
        'ros_distro': '',
    }

    jenkins = connect(args.jenkins_url)

    jenkins_kwargs = {}
    if not args.commit:
        jenkins_kwargs['dry_run'] = True
    pattern_select_jobs_regexp = ''
    if args.select_jobs_regexp:
        pattern_select_jobs_regexp = re.compile(args.select_jobs_regexp)

    def create_job(os_name, job_name, template_file, additional_dict):
        if pattern_select_jobs_regexp and not pattern_select_jobs_regexp.match(job_name):
            return
        job_data = dict(data)
        job_data['ros_distro'] = os_configs[os_name]['ros_distro']
        if job_data['ros_distro'] == 'rolling':
            job_data['default_repos_url'] = DEFAULT_REPOS_URL.format(ros_distro='master')
        else:
            job_data['default_repos_url'] = DEFAULT_REPOS_URL.format(ros_distro=os_configs[os_name]['ros_distro'])
        job_data['os_name'] = os_name
        job_data.update(os_configs[os_name])
        job_data.update(additional_dict)
        job_config = expand_template(template_file, job_data)
        configure_job(jenkins, job_name, job_config, **jenkins_kwargs)

    os_configs = {
        'linux': {
            'label_expression': 'linux',
            'shell_type': 'Shell',
            'ros_distro': '',
        },
        'linux-aarch64': {
            'label_expression': 'linux_aarch64',
            'shell_type': 'Shell',
            'ros_distro' : '',
        },
        'windows': {
            'label_expression': 'windows-container',
            'shell_type': 'BatchFile',
            'use_isolated_default': 'false',
        },
    }

    for os_name in sorted(os_configs.keys()):
        for ros_distro in ['foxy', 'rolling', 'galactic']:
            os_configs[os_name]['ros_distro'] = ros_distro

            create_job(os_name, f'ci_{os_name}_' + os_configs[os_name]['ros_distro'], 'ci_job.xml.em', {
                'cmake_build_type': 'None',
                'time_trigger_spec': PERIODIC_JOB_SPEC,
            })


if __name__ == '__main__':
    main()
