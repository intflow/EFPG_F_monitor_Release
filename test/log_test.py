import subprocess
import os

run_log_command = f"#!/bin/bash\nbash ./run_SR.sh 1> tl1.log 2>&1"
with open("run_SR_with_log.sh", "w") as f:
    f.write(run_log_command)
    
subprocess.run(f"docker cp run_SR_with_log.sh efhall_test:/opt/nvidia/deepstream/deepstream/sources/apps/sample_apps", shell=True)

os.remove("run_SR_with_log.sh")

subprocess.run(f"docker exec -dit efhall_test bash ./run_SR_with_log.sh", shell=True)