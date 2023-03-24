#!/bin/bash
SERVER_IP='intflow@192.168.0.103'

USER_IP='37'

FILE_NAME='/home/intflow/works/VIDEO/records_win/edgefarm_record/'$USER_IP

SSH_PASS='sshpass -p intflow3121'


if $SSH_PASS ssh -o StrictHostKeyChecking=no $SERVER_IP stat $FILE_NAME \> /dev/null 2\>\&1; then echo 'True' ; else echo 'False' ;fi

if $SSH_PASS ssh -o StrictHostKeyChecking=no $SERVER_IP stat $FILE_NAME \> /dev/null 2\>\&1
             then
                     echo True
                     # echo "mount folder exist "
             else
                     echo False
                     # echo "mount folder does not exist So make mounting folder in remote server"
                     # echo intflow3121 | sudo mkdir $USER_IP && sudo touch $USER_IP/mount_key.txt
                     # sudo sshpass -p intflow3121 scp -r ./$USER_IP intflow@192.168.0.103:$FILE_NAME

 fi
