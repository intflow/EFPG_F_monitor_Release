from subprocess import Popen, PIPE
import subprocess
import json
import configs
import os
import re
import datetime as dt
def remove_SR_vid():
    file_list = os.listdir('/edgefarm_config/Recording/')
    for file_name in file_list:
        if file_name[:3]=="SR_":
            os.remove(os.path.join('/edgefarm_config/Recording/',file_name))
        
        
    
    
if __name__ == "__main__":
<<<<<<< HEAD
    subprocess.run("echo intflow3121 | sudo -S reboot", shell=True) 
=======
    now = dt.datetime.now() 
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
    if now_dt.hour==23 and now_dt.minute:
        subprocess.run("echo intflow3121 | sudo -S reboot", shell=True)
        print(now_dt.hour)
        print(now_dt.minute)
        
>>>>>>> 1746f7c65c8d14b5909d7ad631e6db854a1af928
