ef_conf_path=/etc/supervisor/conf.d/edgefarm_monitor.conf
# ef_conf_path=./efmtest.conf
current_path=`pwd`

sudo apt install supervisor -y &&

echo ""
sudo rm -f ${ef_conf_path} &&
echo "[program:edgefarm_monitor]
command = /usr/bin/python3 ${current_path}/for_supervisor.py
directory = ${current_path}
autostart = yes
autorestart = yes
user = intflow
stdout_logfile = ${current_path}/supervisor_log.txt
redirect_stderr = false" | sudo tee -a ${ef_conf_path}
echo ""

sudo service supervisor start &&
sudo supervisorctl reread &&
sudo supervisorctl update &&
sudo supervisorctl start edgefarm_monitor