from subprocess import Popen, PIPE
import json
import configs
import os
from datetime import datetime
now = datetime.now()

now = datetime.now()
print("시 : ", now.hour)
print("분 : ", now.minute)
if now.minute==0 :
    print('00')
