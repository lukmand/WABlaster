#!/bin/bash

# AWS / GCP
#sudo hostnamectl set-hostname aws-blastapp-09
#rsync --progress -e "ssh -i /home/blastapp/Downloads/aws-blastapp.pem" -avL --rsync-path="mkdir -p /home/ubuntu/aws/`hostname`/ && rsync"  log report ubuntu@172.31.33.109:/home/ubuntu/aws/`hostname`/

# DO
#SSHPASS='blastapp'
#rsync -avr --rsh="/usr/bin/sshpass -p $SSHPASS ssh -o StrictHostKeyChecking=no -l blastapp" --rsync-path="mkdir -p /home/blastapp/digitalocean/`hostname`/ && rsync" log blastapp@10.104.0.10:/home/blastapp/digitalocean/`hostname`
