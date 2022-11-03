from subprocess import Popen, PIPE
import json
import configs
import os
import re
from datetime import datetime
def remove_SR_vid():
    file_list = os.listdir('/edgefarm_config/Recording/')
    for file_name in file_list:
        if file_name[:3]=="SR_":
            os.remove(os.path.join('/edgefarm_config/Recording/',file_name))
        
        
    
    
if __name__ == "__main__":
    remove_SR_vid()