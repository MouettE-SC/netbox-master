#!/bin/bash

set -eo pipefail

ansible-playbook -i hosts -e luks_part=/dev/nvme0n1p3 -b master.yml
