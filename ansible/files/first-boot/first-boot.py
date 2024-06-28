#!/usr/libexec/platform-python

import os
from subprocess import run,PIPE
from getpass import getpass
import sys
import string
import readline
from time import sleep
import shutil
import re
import json
import traceback

def check_ip(ip):
    try:
        a, b, c, d = map(int, ip.split('.'))
        return 1<=a<=254 and a != 127 and 0<=b<=254 and 0<=c<=254 and 0<=d<=254
    except:
        return False

def check_ip_prefix(ip):
    try:
        address, prefix = ip.split('/')
        prefix = int(prefix)
        return check_ip(address) and 1<=prefix<=32
    except:
        return False

def header():
    os.system('clear')
    print()
    print("  ==========  Configuration initiale image Netbox  ==========")
    print()

def main():
    header()
    print()
    print("  Disposition de clavier")
    print()
    while True:
        print("  1. AZERTY")
        print("  2. QWERTY")
        print()
        k = input("   => ")
        try:
            k = int(k)
            if k == 1:
                k = "fr-oss"
            elif k == 2:
                k = "us-altgr-intl"
            else:
                print("Entrée invalide")
                continue
            break
        except:
            print("Entrée invalide")
    os.system(f"localectl set-keymap {k}")

    print()
    print(" Configuration de la clé de chiffrement du disque")
    while True:
        print()
        print("Entrer la clé de chiffrement (au moins 12 caractères)")
        luks_pw = getpass('  => ')
        print("Confirmer")
        pw2 = getpass('  => ')
        if len(luks_pw) < 12 or luks_pw != pw2:
            print("Entrée invalide")
        else:
            break

    print()
    print(" Configuration du mot passe administrateur local (ansible)")
    while True:
        print()
        print("Entrer le nouveau mot de passe (au moins 12 caractères)")
        ansible_pw = getpass('  => ')
        print("Confirmer")
        pw2 = getpass('  => ')
        if len(ansible_pw) < 12 or ansible_pw != pw2:
            print("Entrée invalide")
        else:
            break
        
    header()
    while True:
        print()
        print("  Configuration de l'interface réseau")
        print()
    
        while True:
            print("Adresse IPv4")
            print(" auto ou ip/prefix, par exemple 172.17.36.11/24 :")
            ip = input("    [auto] => ")
            if ip == '' or ip == 'auto' or ip == 'dhcp':
                ip = 'dhcp'
                break
            elif check_ip_prefix(ip):
                ip, prefix = ip.split('/')
                break
            print("  Entrée invalide")
    
        print()
    
        gw = ''
        while ip != 'dhcp':
            print("Passerelle par défaut")
            print(" adresse ip, laisser vide si non définie :")
            gw = input("  => ")
            if not gw or check_ip(gw):
                break
            print("  Entrée invalide")
    
        print()
    
        routes=[]
        if ip != 'dhcp':
            routes.clear()
            print("Route(s) statique(s)")
            print(" '<destination> <passerelle>', par exemple 10.2.0.0/16 192.168.57.1 ;")
            print(" laisser vide pour terminer :")
            while True:
                r = input("  => ")
                if not r:
                    break
                try:
                    n, g = r.split(' ')
                    if check_ip_prefix(n) and check_ip(g):
                        routes.append((n, g))
                        print("     OK")
                    else:
                        print("  Entrée invalide")
                except ValueError:
                    print("  Entrée invalide")
    
        header()
        print()
        print("  Récapitulatif réseau")
        print()
        if ip == 'dhcp':
            print("Adresse IP : DHCP")
        else:
            print(f"Adresse IP : {ip}/{prefix}")
        if gw:
            print(f"Passerelle par défaut     : {gw}")
        if routes:
            print("Route(s) statique(s) :")
            for r in routes:
                print(f"  - {r[0]} via {r[1]}")
        print()
        a = input("Modifier cette configuration [o/N] ? ")
        if a and a[0].lower() in ('o', 'y'):
            continue
        break
    
    header()
    print()
    print("Changement du mot de passe ansible")
    rc = run(['chpasswd'], input=f"ansible:{ansible_pw}".encode('utf8'))
    if rc.returncode != 0:
        raise Exception("Impossible de mettre à jour le mot de passe de l'utilisateur ansible !!")
    print()
    print("Mise en place de la clé de chiffrement du disque")
    rc = run(["lsblk", "-Jlo", "NAME,FSTYPE"], stdout=PIPE, stderr=PIPE, encoding='utf8')
    if rc.returncode != 0:
        raise Exception("Impossible de lister les systèmes de fichiers !!")
    l_drive = ''
    for bd in json.loads(rc.stdout)['blockdevices']:
        if bd['fstype'] == 'crypto_LUKS':
            if l_drive:
                raise Exception("Plusieurs partitions chiffrées trouvées !!")
            l_drive = bd['name']

    if not l_drive:
        raise Exception("Partition chiffrée non trouvée")

    rc = run(['cryptsetup', 'luksAddKey', '-v', '--key-file', '/etc/luks/install.keyfile', f'/dev/{l_drive}'], input=luks_pw.encode('utf8'))
    if rc.returncode != 0:
        raise Exception("Impossible de mettre en place la clé LUKS") 

    print()
    print("Suppression de la clé de déchiffrement automatique")
    os.system(f"cryptsetup luksKillSlot -v -q /dev/{l_drive} 1")
    os.unlink('/etc/luks/install.keyfile')
    os.rmdir('/etc/luks')
    os.system("sed -i -e s:/etc/luks/install.keyfile:none: /etc/crypttab")
    os.unlink('/etc/dracut.conf.d/luks.conf')

    print()
    print("Regénération du disque de démarrage")
    os.system("dracut -f")
    
    print()
    print("Application de la configuration réseau")
    rc = run(['nmcli', '-g', 'name,device', 'con'], stdout=PIPE, stderr=PIPE, encoding='utf8')
    if rc.returncode != 0:
        raise Exception("Impossible de récupérer la liste des connexions réseau")
    d = rc.stdout.strip().split('\n')
    if len(d) > 1:
        raise Exception("Plusieurs connexions réseau trouvées !")
    con, dev = d[0].split(':')
    if ip != 'dhcp':
        os.system(f'nmcli con mod "{con}" ipv4.method manual ipv4.address {ip}/{prefix} ipv6.method disabled')
        if gw:
            os.system(f'nmcli con modify "{con}" ipv4.gateway {gw}')
        for n, g in routes:
            os.system(f'nmcli con modify "{con}" +ipv4.routes "{n} {g}"')
    else:
        os.system(f'nmcli con mod "{con}" ipv4.method auto ipv6.method disabled')
    with open('/etc/issue', 'a') as o:
        o.write(f"   NetBox is available at https://\\4{{{dev}}}/\n\n")

    header()
    print()
    print("Nettoyage")
    os.system('systemctl set-default multi-user.target')
    os.unlink("/etc/systemd/system/first-boot.service")
    os.unlink("/etc/systemd/system/first-boot.target")
    shutil.rmtree("/etc/systemd/system/first-boot.target.wants")
    os.system('systemctl daemon-reload')
    os.unlink('/usr/local/sbin/first-boot.py')
    print()
    print("Redémarrage ...")
    sleep(3)

try:
    main()
except:
    traceback.print_exc()
    os.execl('/bin/bash', '/bin/bash')

os.system('systemctl reboot')
