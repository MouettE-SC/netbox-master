#!/bin/bash

set -eo pipefail

ansible-playbook -i hosts -e luks_part=/dev/vda2 -b master.yml
