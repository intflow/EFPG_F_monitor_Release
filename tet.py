from subprocess import Popen, PIPE
import json
import configs
import os
import re
import datetime as dt

        
    
    
if __name__ == "__main__":
    now = dt.datetime.now() 
    trdvc=False
    t=False
    print(now)
    if not trdvc and not t:
        print('d')
    if not t:
        if now.minute>16:
            print('dc')
