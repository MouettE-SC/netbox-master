#!/bin/bash

set -eo pipefail

ansible-playbook -i hosts -b master.yml
