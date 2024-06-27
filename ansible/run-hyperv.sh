#!/bin/bash

set -eo pipefail

ansible-playbook -i hosts -e luks_part=/dev/sda3 -b master.yml
