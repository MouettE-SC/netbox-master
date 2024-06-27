#!/bin/bash

set -eo pipefail

mkdir -p custom
sha256sum -c AlmaLinux-8.10-x86_64-boot.iso.sha256
7z x -y -ocustom AlmaLinux-8.10-x86_64-boot.iso
rm -rf 'custom/[BOOT]'
cp -f netbox-ks-*.cfg custom
cp -f grub.cfg custom/EFI/BOOT
cp -f isolinux.cfg custom/isolinux
git describe --all --long --dirty > custom/iso.build
( cd custom ; mkisofs -o ../AlmaLinux-8.10-x86_64-boot-netbox.iso -b isolinux/isolinux.bin -J -R -l \
                      -c isolinux/boot.cat -no-emul-boot -boot-load-size 4 -boot-info-table \
                      -eltorito-alt-boot -eltorito-platform efi -eltorito-boot images/efiboot.img -no-emul-boot \
                      -graft-points -joliet-long -V "AlmaLinux-8-10-x86_64-dvd" . )
rm -rf custom
