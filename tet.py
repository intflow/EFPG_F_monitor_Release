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
    subprocess.run("echo intflow3121 | sudo -S reboot", shell=True) 
