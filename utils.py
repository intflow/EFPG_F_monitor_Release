import subprocess
from subprocess import Popen, PIPE
import configs
import requests
from requests.auth import HTTPBasicAuth
import threading
import multiprocessing
import random
import getpass
import natsort
import json
import getmac
import time
import socket
import shutil
import os
import datetime as dt
import json
import copy
import pytz
import logging
import firmwares_manager
from dateutil import parser
import re
# import cv2

# current_dir = os.path.dirname(os.path.abspath(__file__))
# now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
# formattedDate = now_dt.strftime("%Y%m%d_%H0000")
# logging.basicConfig(filename='../logs/monitor__.log', level=logging.INFO,format='%(asctime)s %(message)s')


def mklogfile():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
    formattedDate = now_dt.strftime("%Y%m%d_%H0000")
    print(formattedDate+"log파일 생성")
    logging.disable(logging.INFO)
    logging.basicConfig(filename='../logs/'+formattedDate+"_monitor.log", level=logging.INFO,format='%(asctime)s %(message)s')
    # f = open('../logs/'+formattedDate+"_monitor.log", "a", encoding="UTF8")
    # formattedDate2 = now_dt.strftime("%Y%m%d_%H%M%S")
    # f.write(debug_pr
def create_run_with_log_file(file_path, run_sh_name):
    run_log_command = f"#!/bin/bash\nbash {run_sh_name} 1> {file_path} 2>&1"
    run_with_log_sh_name = os.path.splitext(run_sh_name)[0] + "_with_log.sh"
    with open(run_with_log_sh_name, "w") as f:
        f.write(run_log_command)
    subprocess.run(f"docker cp {run_with_log_sh_name} efhall_test:/opt/nvidia/deepstream/deepstream/sources/apps/sample_apps", shell=True)
    os.remove(run_with_log_sh_name)
    return run_with_log_sh_name

def get_log_file_list(dirpath):
    file_list = [x for x in os.listdir(dirpath) if os.path.splitext(x)[-1] == ".log"]
    file_list.sort(key = lambda f: os.path.getmtime(os.path.join(dirpath, f)), reverse=True)
    
    return file_list

def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def check_log_dir_vol():
    logging.info("\nCheck log dir volume!")    
    
    if get_dir_size(configs.log_save_dir_path_host) >= configs.log_max_volume:
        log_f_list = get_log_file_list(configs.log_save_dir_path_host)
    
        while get_dir_size(configs.log_save_dir_path_host) >= configs.log_max_volume:
            if len(log_f_list) == 0:
                break
            # python_log(f"Remove \"{os.path.join(configs.log_save_dir_path_host, log_f_list[-1])}\"")
            os.remove(os.path.join(configs.log_save_dir_path_host, log_f_list[-1]))
            del log_f_list[-1]
    logging.info("Done!\n")
    
def log_dir_vol_manage(now_dt, LOG_DIR_CHECK):
    if now_dt.minute == 0 and now_dt.second == 0:
    # if now_dt.second == 0:
        if LOG_DIR_CHECK == False:
            check_log_dir_vol()
            LOG_DIR_CHECK = True
    else:
        LOG_DIR_CHECK = False  
    
    return LOG_DIR_CHECK 

def port_status_check(port):
    try:
        res = subprocess.check_output("netstat -ltu | grep {}".format(port), shell=True)
        res = res.decode().split('\n')[:-1]
    except subprocess.CalledProcessError:
        res = []
        
    if len(res) > 0 and res[0].split()[-1] == "LISTEN":
        return True
    else:
        return False
    
def port_process_kill(port):
    try:
        output = subprocess.check_output("sudo -S netstat -nap | grep {}".format(port), stderr=subprocess.PIPE, shell=True)
        output = output.decode().split('\n')[:-1]
        # python_log(output)
    except subprocess.CalledProcessError:
        output = []
    
    if len(output) > 0:
        output = output[0].split()[-1].split('/')[0]
        subprocess.run("sudo -S kill -9 {}".format(output), shell=True)
        # python_log(f'kill {output}')

def kill_edgefarm():
    logging.info(f"docker exec -it {configs.container_name} bash ./kill_edgefarm.sh")
    subprocess.run(f"docker exec -it {configs.container_name} bash ./kill_edgefarm.sh", shell=True)
    
def rm_docker():
    logging.info(f"docker stop {configs.container_name} ")
    subprocess.run(f"docker stop {configs.container_name} ", shell=True)
    
def run_docker(docker_image, docker_image_id):
    firmwares_manager.copy_firmwares()
    device_install()
    fan_speed_set(configs.FAN_SPEED)
    if docker_image == None or docker_image_id == None:
        for i in range(10):
            logging.info("\nNo Docker Image...\n")
        return -1
    if (check_deepstream_status()): # engine 켜져있다면
        rm_docker()
    
    run_docker_command = "docker run -dit "\
                        + "--rm "\
                        + f"--name={configs.container_name} "\
                        + "--net=host "\
                        + "--privileged "\
                        + "--ipc=host "\
                        + "--runtime nvidia "\
                        + "-v /edgefarm_config:/edgefarm_config "\
                        + "-v /home/intflow/works:/works "\
                        + "-w /opt/nvidia/deepstream/deepstream-6.0/sources/apps/sample_apps "\
                        + f"{docker_image_id} bash "
                        # + "{} bash".format(lastest_docker_image_info[1])
    logging.info(run_docker_command)
    logging.info(f"Docker Image : {docker_image}\n")
    subprocess.call(run_docker_command, shell=True)
    logging.info("\nDocker run!\n")
def read_elapsed_time():
    elapsed_times = []
    try:
        with open("/edgefarm_config/elapsed.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line.isdigit():
                    elapsed_times.append(int(line))
    except FileNotFoundError:
        return None
    return elapsed_times
def get_deepstream_time():
    from datetime import datetime, timedelta
    elapsed_times = read_elapsed_time()
    if elapsed_times:
        deepstream_time = sum(elapsed_times) / len(elapsed_times)
    else:
        deepstream_time = None
    # deepstream_time_td = timedelta(minutes=deepstream_time)
    return deepstream_time
aws_start=True
def run_SR_docker(aws_start):
    run_sh_name = "run_SR.sh"
    mklogfile()
    os.makedirs(configs.log_save_dir_path_host, exist_ok=True)

    KST_timezone = pytz.timezone('Asia/Seoul')
    now_kst = dt.datetime.now().astimezone(KST_timezone)
    deepstream_time = get_deepstream_time()
    deepstream_minutes = int(deepstream_time) if deepstream_time is not None else 0
    remaining_second=3600-(now_kst.minute * 60 + now_kst.second)
    if remaining_second-deepstream_minutes>180:
        aws_start=True
        # run_count=remaining_second/deepstream_minutes
        # logging.info(str(run_count)+" 번은 돌릴수 있겠다.")
        file_name = now_kst.strftime("%Y%m%d_%H%M%S_.log")
        file_path = os.path.join(configs.log_save_dir_path_docker, file_name)
        # now_kst.minute
        run_with_log_sh_name = create_run_with_log_file(file_path, run_sh_name)
            
        remove_SR_vid()
        # file_list = os.listdir(configs.recordinginfo_dir_path)
        # subprocess.run(f"docker exec -dit {configs.container_name} bash ./run_SR.sh 1> {file_path} 2>&1", shell=True)
        # subprocess.run(f"docker exec -dit {configs.container_name} bash ./run_SR_with_log.sh 1> {file_path} 2>&1", shell=True)
        
        subprocess.run(f"docker exec -dit {configs.container_name} bash {run_with_log_sh_name}", shell=True)
        python_log(f"\nThe real-time log is being saved at \"{os.path.join(configs.log_save_dir_path_host, file_name)}\"\n")
    else:
        try:
            # aws_thread_list = []
            # aws_thread_mutex = threading.Lock()
            # aws_thread_cd = threading.Condition()
            # aws_thread_list.append(threading.Thread(target=matching_cameraId_ch, name="matching_cameraId_ch", daemon=True))
            # aws_thread_list[0].start()
            if aws_start:
                matching_cameraId_ch2()
                aws_start=False
                # clear_orderData()
                # subprocess.run("rm -rf "+configs.METADATA_DIR+"/*", shell=True) 
        except Exception as e:
            logging.ERROR(e)
    return aws_start
def export_model(docker_image, docker_image_id, mode=""):
    deepstream_exec=False
    SR_exec=False
    for line in Popen(['ps', 'aux'], shell=False, stdout=PIPE).stdout:
        result = line.decode('utf-8')
        if result.find('deepstream-SR')>1: # deepstream이 ps에 있는지 확인
            SR_exec=True
            logging.info("smart record 실행중")
            break  
        if result.find('deepstream-custom-pipeline')>1: # deepstream이 ps에 있는지 확인
            deepstream_exec=True
            logging.info("file sink 가 실행중")
            break  
    print("export model!\n")
    if not deepstream_exec and not SR_exec:
        subprocess.run(f"docker exec -dit {configs.container_name} bash export_model.sh ", shell=True)
    # print(run_docker_command)
def edgefarm_config_check():
    # /edgefarm_config 가 없으면 전체 복사
    if os.path.isdir("/edgefarm_config") == False:
        subprocess.run("sudo mkdir /edgefarm_config", shell=True)
        print("make directory /edgefarm_config")
    subprocess.run("sudo chown intflow:intflow -R /edgefarm_config", shell=True)
    
    git_edgefarm_config_path = os.path.join(current_dir, "edgefarm_config")
    
    # 모델 관련 파일이 있나 검사. 하나라도 없으면 복사해주고 모델 export
    model_related_list = ['model', 'model/intflow_model.onnx', 'model/intflow_model.engine']
    no_model = False
    for m_i in model_related_list:
        tmp_p = os.path.join(configs.local_edgefarm_config_path, m_i)
        if not os.path.exists(tmp_p):
            no_model = True
    if no_model:    
        model_update(mode='sync')
def model_update(mode=""):
    local_model_file_path = os.path.join(configs.local_edgefarm_config_path, configs.local_model_file_relative_path)
    
    # 인터넷 안되면 monitor 에 있는 model 복사
    if not configs.internet_ON:
        subprocess.run(f"sudo cp {os.path.join(current_dir, 'edgefarm_config/model/intflow_model.onnx')} {local_model_file_path}")
    else:    
        # /edgefarm_config/model 디렉토리가 없으면 생성.
        if not os.path.exists(os.path.join(configs.local_edgefarm_config_path, "model")):
            os.makedirs(os.path.join(configs.local_edgefarm_config_path, "model"), exist_ok=True)
            
        serial_number = read_serial_number()
        
        print("Start Model Update!")
        
        model_file_name = f"{serial_number}/{configs.server_model_file_name}"
        
        # 서버에서 모델 파일 복사해오기
        # copy_to(os.path.join(git_edgefarm_config_path, "model/intflow_model.onnx"), os.path.join(configs.local_edgefarm_config_path, "model/intflow_model.onnx"))
        subprocess.run(f"aws s3 cp s3://{configs.server_bucket_of_model}/{model_file_name} {local_model_file_path}", shell=True)
    
    docker_image, docker_image_id = find_lastest_docker_image(configs.docker_repo)
    # onnx to engine
    export_model(docker_image, docker_image_id, mode=mode)
    # # 버전 파일 복사.
    if mode == "sync" : print("\nModel Update Completed")    
def run_file_deepstream_docker():
    run_sh_name = "run_filesink.sh"
    # check_SR_file()
    
    os.makedirs(configs.log_save_dir_path_host, exist_ok=True)
    
    KST_timezone = pytz.timezone('Asia/Seoul')
    now_kst = dt.datetime.now().astimezone(KST_timezone)
    
    file_name = now_kst.strftime("%Y%m%d_%H%M%S_FileSink.log")
    file_path = os.path.join(configs.log_save_dir_path_docker, file_name)
    
    run_with_log_sh_name = create_run_with_log_file(file_path, run_sh_name)
    # subprocess.run(f"docker exec -dit {configs.container_name} bash ./run_filesink.sh", shell=True)
    subprocess.run(f"docker exec -dit {configs.container_name} bash {run_with_log_sh_name}", shell=True)
    logging.info("\nDocker run!\n")
    logging.info(f"\nThe real-time log is being saved at \"{os.path.join(configs.log_save_dir_path_host, file_name)}\"\n")
def check_SR_file():
    file_list = os.listdir('/edgefarm_config/Recording/')
    file_list.sort(key=lambda x: os.stat(x).st_mtime)
    SR_list=[]
    for file_name in file_list:
        if file_name[:3]=="SR_":
            if int(file_name[3]) in SR_list:
                logging.info(file_name+"중복제거 ")
                os.remove(os.path.join('/edgefarm_config/Recording/',file_name))
            else:    
                SR_list.append(int(file_name[3]))
            

def fan_speed_set(speed):
    # 팬 속도
    subprocess.run("sudo -S sh -c 'echo {} > /sys/devices/pwm-fan/target_pwm'".format(speed), stderr=subprocess.PIPE, shell=True)

## 실행 중이면 True, 실행 중이 아니면 False 반환.
def check_deepstream_status():
    res = subprocess.check_output("docker ps --format \"{{.Names}}\"", shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]
    
    # python_log(res)

    if configs.container_name in res:
        return True
    else:
        return False
    

def current_running_image(docker_image_head):
    res = subprocess.check_output("docker images --filter=reference=\"{}*\" --format \"{{{{.Tag}}}} {{{{.ID}}}}\"".format(docker_image_head), shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]
    res = [i.split(" ") for i in res]
    res = natsort.natsorted(res, key = lambda x: x[0], reverse=True)
    # python_log(res)

    c_image_id = None
    c_image_name = None
    c_res = subprocess.check_output("docker ps --format \"{{.Names}} {{.Image}}\"", shell=True)
    c_res = str(c_res, 'utf-8').split("\n")[:-1]
    c_res = [i.split(" ") for i in c_res]
    # python_log(c_res)

    for container_name, image in c_res:
        if container_name == configs.container_name:
            c_image_id = image
            # python_log(c_image_id)
        
    if c_image_id is not None:
        for image_name, image_id in res:
            if image_id == c_image_id:
                # python_log(image_name)
                c_image_name = image_name
    
    return c_image_name

def find_lastest_docker_image(docker_image_head, mode=0):
    res = subprocess.check_output("docker images --filter=reference=\"{}*\" --format \"{{{{.Tag}}}} {{{{.ID}}}}\"".format(docker_image_head), shell=True)
    res = str(res, 'utf-8').split("\n")[:-1]
    if len(res) == 0:
        return [None, None]
    
    res = [i.split(" ") for i in res]

    res = natsort.natsorted(res, key = lambda x: x[0], reverse=True)
    
    if mode == 1:
        logging.info(f"\n{docker_image_head} docker image list")
        for i in res:
            logging.info('  ', i)
    
    return res[0]

def docker_pull(docker_repo, last_docker_image_dockerhub):
    if configs.docker_id == None or configs.docker_pw == None:
        configs.docker_id = input("UserID for 'https://hub.docker.com/': ")
        configs.docker_pw = getpass.getpass("Password for 'https://hub.docker.com/': ")        
    subprocess.run(f"docker login docker.io -u \"{configs.docker_id}\" -p \"{configs.docker_pw}\"", shell=True)
    subprocess.run("docker pull {}".format(docker_repo + ":" + last_docker_image_dockerhub), shell=True)
    subprocess.run("docker logout", shell=True)

def docker_image_tag_api(image):
    docker_api_host = "https://registry.hub.docker.com"
    path = "/v1/repositories/" + image + "/tags"
    url = docker_api_host + path
    configs.docker_id = input("UserID for 'https://hub.docker.com/': ")
    configs.docker_pw = getpass.getpass("Password for 'https://hub.docker.com/': ")
    # python_log(url)
    try:
        response = requests.get(url,auth = HTTPBasicAuth(configs.docker_id, configs.docker_pw))

        logging.info("response status : %r" % response.status_code)
        return response.json()
    except Exception as ex:
        logging.error(ex)
        return None
    
def search_dockerhub_last_docker_image(docker_repo, tag_header):
    # res = docker_image_tag_api('intflow/edgefarm')
    res = docker_image_tag_api(docker_repo)
    
    current_image = find_lastest_docker_image(docker_repo + ":" + tag_header)[0]
    
    if res is not None:
        image_tag_list = []

        for each_r in res:
            # python_log(each_r["name"])
            # if "hallway_dev" in each_r["name"]:
            if tag_header in each_r["name"]:
                # python_log(each_r["name"])
                image_tag_list.append(each_r["name"])
                
        image_tag_list = natsort.natsorted(image_tag_list, key = lambda x: x, reverse=True)
        
        if len(image_tag_list) > 0:
            if current_image is None:
                update_history = len(image_tag_list)
            else:
                if current_image in image_tag_list:
                    update_history = image_tag_list.index(current_image)
                else:
                    update_history = -1
            return [image_tag_list[0], update_history]
        else:
            return ["None", -1]
    else:
        return ["None" -1]

def send_api(path, mac_address):
    url = configs.API_HOST + path + '/' + mac_address

    logging.info(url)
    
    try:
        response = requests.get(url)

        logging.info("response status : %r" % response.status_code,)
        return response.json()
    except Exception as ex:
        logging.error(ex)
        return None
def check_aws_install():
    res = os.popen('which aws').read()

    if "/usr/local/bin/aws" in res:
        print("AWS CLI installed")
        pass
    else:
        print("Install AWS CLI ...")
        subprocess.run("bash ./aws_cli_build.sh", shell=True)
        
    mac_address = getmac.get_mac_address()
    serial_number=read_serial_number()
        
    akres = send_ak_api("/device/upload/key", mac_address, serial_number)

    if not os.path.isdir("/home/intflow/.aws"):
        os.makedirs("/home/intflow/.aws", exist_ok=True)
        
    subprocess.run('sudo chown intflow:intflow /home/intflow/.aws -R', shell=True)

    with open("/home/intflow/.aws/credentials", "w") as f:
        f.write(f"[default]\naws_access_key_id = {akres['access']}\naws_secret_access_key = {akres['secret']}\n")
def get_local_model_mtime():
    local_model_file_path = os.path.join(configs.local_edgefarm_config_path, configs.local_model_file_relative_path)
    
    if not os.path.exists(local_model_file_path):
        return None
    
    kst = pytz.timezone('Asia/Seoul')
    
    last_modified_local = os.path.getmtime(local_model_file_path)

    last_modified_local = dt.datetime.fromtimestamp(last_modified_local)
    last_modified_local = kst.localize(last_modified_local)    
    
    return last_modified_local
def send_ak_api(path, mac_address, serial_number):
    url = configs.API_HOST2 + path + '/' 
    content={}
    content['mac_address']=mac_address
    content['serial_number']=serial_number
    print(url)
    
    try:
        # response = requests.post(url, data=json.dumps(metadata))
        response = requests.put(url, json=content)

        print("response status : %r" % response.status_code)
        if response.status_code == 200:
            # return True
            return response.json()
        else:
            # return False
            return None
        # return response.json()
    except Exception as ex:
        print(ex)
        # return False
        return None 
def send_json_api(path, mac_address,serial_number,firmware_version):
    url = configs.API_HOST2 + path + '/' 
    content={}
    content['mac_address']=mac_address
    content['serial_number']=serial_number
    content['version']=firmware_version
    print(url)
    
    try:
        # response = requests.post(url, data=json.dumps(metadata))
        response = requests.put(url, json=content)

        print("response status : %r" % response.status_code)
        if response.status_code == 200:
            # return True
            return response.json()
        else:
            # return False
            return None
        # return response.json()
    except Exception as ex:
        print(ex)
        # return False
        return None
def key_match(src_key, src_data, target_data):
    if src_key in configs.key_match_dict:
        target_key = configs.key_match_dict[src_key]
        if target_key in target_data:
            target_val = target_data[target_key]
            logging.info(f"{src_key} : {src_data[src_key]} -> {target_val}")
            src_data[src_key] = target_val 
            
def read_serial_number():
    with open(os.path.join(configs.local_edgefarm_config_path, "serial_number.txt"), 'r') as mvf:
        serial_numbertxt = mvf.readline()
    return serial_numbertxt.split('\n')[0]

def read_firmware_version():
    with open(os.path.join(configs.firmware_dir, "__version__.txt"), 'r') as mvf:
        firmware_versiontxt = mvf.readline()
    return firmware_versiontxt.split('\n')[0]

def device_install():
    try:
        # mac address 뽑기
        mac_address = getmac.get_mac_address()
        check_aws_install()
        mkdir_logs()
        serial_number=read_serial_number()
        firmware_version=read_firmware_version()
        docker_repo = configs.docker_repo
        docker_image, docker_image_id = find_lastest_docker_image(docker_repo)
        docker_image_tag_header = configs.docker_image_tag_header
        e_version=docker_image.replace(docker_image_tag_header+'_','').split('_')[0]
        device_info=send_json_api(configs.access_api_path, mac_address, serial_number, firmware_version)
        
        # print(device_info)
        
        # 기존 파일들 삭제
        if os.path.isdir(configs.roominfo_dir_path):
            shutil.rmtree(configs.roominfo_dir_path)    
        os.mkdir(configs.roominfo_dir_path)

        params_of_room = [
            "id", 
            "device_id", 
            "name", 
            "weight_bias", 
            "age", 
            "chessboard_cm", 
            "chessboard_px",
            "vpi_k1",
            "vpi_k2",
            "x_focus",
            "y_focus",
            "x_pad",
            "y_pad",
            "x_rotate",
            "y_rotate",
            "x_scale",
            "y_scale",
            "zx_perspect",
            "zy_perspect",
            "detection_area",
            "food_area"
            ]

        key_match = {
            "chessboard_cm" : "grow_width_cm",
            "chessboard_px" : "grow_width_pixel"
        }

        total_room_info_list = []

        for a_dict in device_info['camera_list']:
            rtsp_value = a_dict["rtsp"]
            b_dict_index = None
            
            for i, b_dict in enumerate(total_room_info_list):
                if b_dict["rtsp"] == rtsp_value:
                    b_dict_index = i
                    break
            
            if b_dict_index is None:
                b_dict = {"rtsp": rtsp_value, "info": []}
                total_room_info_list.append(b_dict)
            else:
                b_dict = total_room_info_list[b_dict_index]
            
            b_dict_info = {}
            for key, value in a_dict.items():
                if key in params_of_room:
                    if key in key_match.keys():
                        key = key_match[key]
                    b_dict_info[key] = value
            b_dict["info"].append(b_dict_info)

        for i, item in enumerate(total_room_info_list):
            file_name = f"room{i}.json"
            
            with open(os.path.join(configs.roominfo_dir_path, file_name), "w", encoding="utf-8") as f:
                json.dump(item, f, ensure_ascii=False)  
                
    except Exception as e:
        logging.ERROR(e)

def create_food_area():
    file_list = os.listdir(configs.roominfo_dir_path)
    for file_name in file_list:   
        with open(os.path.join(configs.roominfo_dir_path, file_name), "r") as json_file:
            content = json.load(json_file)
        match = re.search(r'room(\d+)', file_name)

        if match:
            room_number_str = match.group(1)
            room_number=int(room_number_str)
            # print(configs.roiinfo_dir_path+"/roi"+room_number_str+".json")
        info_num=0
        json_data={}
        for j_info in content["info"] :
            info_num=info_num+1
            if j_info["food_area"]==None:
                print("~~~")
            else:
                my_list = j_info["food_area"].split(',')
                result = [list(map(int, my_list[i:i+4])) for i in range(0, len(my_list), 4)]
                for i ,result2 in enumerate(result):
                    info_num=info_num+i
                    json_data["EAT"+str(info_num)]=result2
           
        with open(configs.roiinfo_dir_path+"/roi"+room_number_str+".json", "w") as f:
            json.dump(json_data, f)
                
def docker_log_end_print():
    print("\n===========================================")
    print("       View docker log mode End")
    print("===========================================\n")
    # control_thread_mutex.release()
    
def docker_log_view():
    ## docker log 보는 subprocess 실행
    docker_log = subprocess.Popen(f"docker logs -f -t --since=24h {configs.container_name}", stdout=subprocess.PIPE, shell=True)

    while docker_log.poll() == None:
        out = docker_log.stdout.readline()
        logging.info(out.decode(), end='')

    docker_log_end_print()
def model_update_check(check_only = False):
    if not configs.internet_ON:
        return
     
    print("Check Model version...")
    lastest = True
    
    serial_number = read_serial_number()

    model_file_name = f"{serial_number}/{configs.server_model_file_name}"
    
    logging.info(f"s3://{configs.server_bucket_of_model}/{model_file_name}")

    try:
        res = subprocess.check_output(f"aws s3api head-object --bucket {configs.server_bucket_of_model} --key {model_file_name}", shell=True)
    except Exception as e:
        logging.ERROR("Can not find model file in server!")
        logging.ERROR(e)
        return False
        
    res_str = res.decode()

    model_file_metadata = json.loads(res_str)
    model_file_metadata["LastModified"]

    last_modified_server_string = model_file_metadata["LastModified"]
    last_modified_server = parser.parse(last_modified_server_string)

    kst = pytz.timezone('Asia/Seoul')

    last_modified_server = last_modified_server.astimezone(kst)
    last_modified_local = get_local_model_mtime()
    if last_modified_local is None:
        print("Can not find model file in local!")
        return False

    logging.info(f"  server : {last_modified_server}")
    logging.info(f"  local  : {last_modified_local}")

    #date_kst
    if last_modified_server > last_modified_local:
        print("Model Update required...")
        lastest = False
    elif last_modified_server <= last_modified_local:
        print("Lastest version of model")

    if not check_only and lastest == False:
        # 혹시 엣지팜 켜져있으면 끄기.
        model_update(mode='sync')
        
    return True

def show_docker_images_list(docker_image_head):
    subprocess.run("docker images --filter=reference=\"{}*\"".format(docker_image_head), shell=True)

def port_info_set():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    configs.last_ip=s.getsockname()[0].split('.')[-1]

    with open(configs.edgefarm_port_info_path, 'r') as port_info_f:
        content = port_info_f.readlines()
        num_line = len(content)

        if configs.last_ip is not None:
            configs.PORT = int(configs.last_ip + str(configs.device_socket_port_end))
            configs.http_server_port = int(configs.last_ip + str(configs.http_server_port_end))
            if num_line >= 3:
                udp_host = "224.224.255." + configs.last_ip + "\n"
                content[2] = udp_host

                configs.engine_socket_port = configs.last_ip + str(configs.engine_socket_port_end)

                if num_line >= 4:
                    content[3] = configs.engine_socket_port + "\n"
                    content[4] = str(configs.PORT) + "\n"
                    content[5] = str(configs.http_server_port) + "\n"
                else:
                    content.append(configs.engine_socket_port + "\n")
                    content.append(str(configs.PORT) + "\n")
                    content.append(str(configs.http_server_port) + "\n")

    with open(configs.edgefarm_port_info_path, 'w') as port_info_f:
        port_info_f.writelines(content)
        
        
def send_meta_api(cam_id_, data):
    uri_param = "/camera/hour/data"
    url = configs.API_HOST + uri_param + '/' + str(cam_id_)

    logging.info("API: "+url)
    logging.info(data)
    
    try:
        # response = requests.post(url, data=json.dumps(metadata))
        response = requests.post(url, json=data)

        logging.info("response status : %r" % response.status_code)
        if response.status_code == 200:
            return True
        else:
            return False
        # return response.json()
    except Exception as ex:
        logging.error(ex)
        return False
        # return None
def metadata_info():
    meta_f_list = os.listdir(configs.METADATA_DIR)
    for i, each_f in enumerate(meta_f_list):
        with open(os.path.join(configs.METADATA_DIR, each_f), "r") as json_file:
            content = json.load(json_file)
# 메타정보 보내는
def metadata_send_ready():
    meta_f_list = os.listdir(configs.METADATA_DIR)
    for i, each_f in enumerate(meta_f_list):
        with open(os.path.join(configs.METADATA_DIR, each_f), "r") as json_file:
            content = json.load(json_file)
        content["updated"]=True
        print("강제로 메타정보 보낼 준비 하겠습니다.")
        with open(os.path.join(configs.METADATA_DIR, each_f), "w") as json_file:
            json.dump(content, json_file)
def metadata_send():
    meta_f_list = os.listdir(configs.METADATA_DIR)
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9))) # 2022-10-21 17:22:32
    now_dt_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_dt_str_for_vid_name = now_dt.strftime("%Y%m%d%H")
    res = [False for i in range(len(meta_f_list))]

    for i, each_f in enumerate(meta_f_list):
    # each_f = meta_f_list[0]
        content_og = None
        with open(os.path.join(configs.METADATA_DIR, each_f), "r") as json_file:
            content = json.load(json_file)
            content_og = copy.deepcopy(content)
            cam_id = -1
            source_id = -1
            if "updated" not in content: # updated 없으면 패스
                logging.info('[updated key가 없어요]')
                logging.info(content)
                continue
            if content["updated"] == False: # updated False 면 패스
                logging.info('[보냈는데 다시 보낼수 없어.]')
                logging.info(content)
                continue
            else: # updated 있으면
                content.pop('updated') # updated pop
                content_og["updated"] = False # False 로 변경.
            # if "created_datetime" not in content:
            content["created_datetime"] = now_dt_str
            content_og["created_datetime"] = now_dt_str
            if "cam_id" in content:
                cam_id = content.pop('cam_id')
            if "source_id" in content:
                source_id = content.pop('source_id')
            overlay_vid_name = "efpg_" + now_dt_str_for_vid_name + f"_{source_id}CH.mp4"
            # if content["activity"]>configs.good_activity:
            #     logging.info("활동량이  "+str(content["activity"])+"kal 이므로"+str(content["activity"])+" 카메라 동영상 보내겠습니다. ")
            #     content['video_path'] = overlay_vid_name
            file_name_without_extension = os.path.splitext(overlay_vid_name)[0]
            content['thumbnail_path'] = file_name_without_extension+".jpg"
            python_log(content)          
            if send_meta_api(cam_id, content) == True:
                res[i] = True
                os.remove(configs.METADATA_DIR+"/"+ each_f)
            print(content)
                
                
        subprocess.run("sudo chmod -R 777 "+ configs.METADATA_DIR, shell=True)
        print()
        # 보내고 난 다음에 updated 가 False 로 바꾼 것들을 저장.
        if content_og is not None:
            with open(os.path.join(configs.METADATA_DIR, each_f), "w") as json_file:
                json.dump(content_og, json_file)
                
    return res
def mkdir_logs():
    import os
    import stat
    log_folder = "../logs"
    if not os.path.exists(log_folder):
        os.makedirs(log_folder, mode=0o777)
        os.chmod(log_folder, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

# def cut_video(video_path, cut_length):
    # try:
    #     from moviepy.video.io.VideoFileClip import VideoFileClip
    # except ModuleNotFoundError:
    #     subprocess.call(['pip3', 'install', 'moviepy'])
    #     from moviepy.video.io.VideoFileClip import VideoFileClip

    # # 원본 동영상 경로와 자를 동영상의 길이를 입력합니다.
    # # video_path = "original_video.mp4"
    # # cut_length = 60  # 자를 길이 (초)

    # # 원본 동영상을 읽어옵니다.
    # video = VideoFileClip(video_path)

    # # 동영상의 길이가 5분 이상이면 작업을 진행합니다.
    # if video.duration >= 70:
    #     # 자를 길이에 맞게 동영상을 자릅니다.
    #     last_frame = video.to_ImageClip(t=video.duration)
    #     cut_video = video.subclip(video.duration - cut_length, video.duration)
    #     # 자른 동영상을 저장합니다.
    #     cut_video.write_videofile(video_path)
    #     last_frame.save_frame(video_path.split('.')[0] + ".jpg")
    # else:
    #     print("동영상의 길이가 1분 미만입니다.")
def python_log(debug_print):
    print(debug_print)
    if isinstance(debug_print, str):
        now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
        formattedDate = now_dt.strftime("%Y%m%d_%H0000")
        f = open('../logs/'+formattedDate+"_monitor.log", "a", encoding="UTF8")
        formattedDate2 = now_dt.strftime("%Y%m%d_%H%M%S")
        f.write(debug_print+'\n')
        f.close()
def internet_check():
    try:
        # connect to the host -- tells us if the host is actually reachable
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        logging.info("Check Internet : Success")
        return True
    except socket.timeout:
        logging.info("Check Internet : Failed(Timeout)")
        return False
    except:
        logging.info("Check Internet : Failed")
        return False         
# deepstream 실행 횟수 json을 0으로 클리어 하는
def clear_deepstream_exec():
    with open(configs.deepstream_num_exec, 'r') as f:

        json_data = json.load(f)

    json_data['deepstream_smartrecord']=0
    json_data['deepstream_filesink']=0
    json_data['DB_insert']=0
    
    
    
    with open(configs.deepstream_num_exec, 'w') as f:
        json.dump(json_data, f)

        
def remove_SR_vid(): # 레코드 폴더에 있는 SR 이름 다 지우기 
    file_list = os.listdir('/edgefarm_config/Recording/')
    with open('/edgefarm_config/switch_status.txt', 'r') as file:
        content = file.read()
    my_bool = bool(int(content)) # True
    for file_name in file_list:
        if file_name[:3]=="SR_":
            if my_bool:
                number = int(file_name[3])
                with open(os.path.join(configs.roominfo_dir_path+ "/room"+str(number)+".json"), "r") as f:
                    json_data = json.load(f)
                for j_info in json_data["info"]:
                    cam_id=j_info["id"]
                    print(cam_id)
                    SR_path='/edgefarm_config/Recording/'+file_name
                    subprocess.run("aws s3 cp "+SR_path+" s3://intflow-data/"+str(cam_id)+"/"+file_name, shell=True)
                    logging.info("aws s3 cp "+SR_path+" s3://intflow-data/"+str(cam_id)+"/"+file_name)
            # os.remove(os.path.join('/edgefarm_config/Recording/',file_name))
       
def cam_id_info(cam_id ,activity ):
    over_activity=False
    cam_id=str(cam_id)
    if os.path.isfile(configs.local_edgefarm_config_path+"/activity_data.json"):
        with open(configs.local_edgefarm_config_path+"/activity_data.json", "r") as f:
            activity_data= json.load(f)
        if cam_id not in activity_data:
            # cam_id가 새로운 경우, 새로운 객체 생성
            logging.info("cam_id가 새로운 경우, 새로운 객체 생성")
            activity_data[cam_id] = {"average_activity": activity, "activity_count": 1}
        else:
            logging.info("cam_id가 이미 있는 경우, 기존 정보 가져오기")
            
            # cam_id가 이미 있는 경우, 기존 정보 가져오기
            avg_activity = activity_data[cam_id]["average_activity"]
            if activity>avg_activity:
                over_activity=True
                logging.info("activity가 높다!!")
            activity_count = activity_data[cam_id]["activity_count"]
            total=avg_activity*activity_count
            total=total+activity
            activity_count=activity_count+1
            avg_activity=total/activity_count
            activity_data[cam_id]["average_activity"] = avg_activity
            activity_data[cam_id]["activity_count"] = activity_count
        with open(configs.local_edgefarm_config_path+"/activity_data.json", 'w') as f:
            json.dump(activity_data, f)
    else:
        print("값이 없다.")
        activity_data = {}
        activity_count =1
        activity_data[cam_id]= {"average_activity": activity, "activity_count": activity_count}
        with open(configs.local_edgefarm_config_path+"/activity_data.json", 'w') as f:
            json.dump(activity_data, f, indent=4)
    return over_activity

def matching_meta_date():
    file_list = os.listdir(configs.MetaDate_path)
    result_dict ={}
    max_act_vid_list={}
    file_list.sort()
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9))) # 2022-10-21 17:22:32
    now_dt_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_dt_str_for_vid_name = now_dt.strftime("%y%m%d%H")
    print(now_dt_str_for_vid_name)
    for file_name in file_list:
        if "metadata_grow" in file_name and "ch" in file_name and "st" in file_name  and now_dt_str_for_vid_name in file_name:
            if file_name.endswith(".json"):
                start = file_name.find("metadata_grow_") + len("metadata_grow_")
                end = file_name.find("ch", start)
                result = int(file_name[start:end])
                if result in result_dict:
                    result_dict[result].append(file_name)
                else:
                    result_dict[result] = [file_name]
    
    for ch_num, filelist in result_dict.items():
        dict_list =[]
        for filename in filelist:
            with open(configs.MetaDate_path+"/"+filename, 'r') as f1:
                data1 = json.load(f1)
            dict_list.append(data1)
        result_dict = {}
        for dictionary in dict_list:
            for key, value in dictionary.items():
                if key in result_dict:
                    result_dict[key].append(value)
                else:
                    result_dict[key] = [value]
        sum_dic ={}
        sum_dic['activity']=sum(result_dict['activity'])
        sum_dic['amount_food']=sum(result_dict['amount_food'])
        sum_dic['cam_id']=max(result_dict['cam_id'])
        sum_dic['pollution']=max(result_dict['pollution'])
        sum_dic['source_id']=max(result_dict['source_id'])
        sum_dic['stocks']=max(result_dict['stocks'])
        sum_dic['updated']=min(result_dict['updated'])
        # sum_dic['weight']=sum(result_dict['weight']) / len(result_dict['weight'])
        sum_json_name="metadata_grow_"+str(ch_num)+"ch.json"
        max_index_act = result_dict['activity'].index(max(result_dict['activity']))+1
        max_index_stocks = result_dict['stocks'].index(max(result_dict['stocks']))
        max_index_weight = result_dict['weight'].index(max(result_dict['weight']))
        sum_dic['weight_list']=result_dict['weight_list'][max_index_stocks]
        
        sum_dic['weight_list'],sum_dic['weight'],_=grow_sampling_weightlist(int(sum_dic['stocks']),sum_dic['weight_list'])
        #metadata_grow_580ch.json
        now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
        current_time = now_dt.strftime("%Y%m%d%H")
        # print(current_time)
        file_list = os.listdir(configs.recordinginfo_dir_path)
        max_act_vid="efpg_"+current_time+"_"+str(max(result_dict['source_id']))+"CH_"+str(max_index_act)+"st.mp4"
        with open(configs.MetaDate_path+"/"+sum_json_name, "w") as f:
            json.dump(sum_dic, f)
        img_name = os.path.splitext(max_act_vid)[0]+".jpg"
        max_act_vid_list[sum_json_name]=max_act_vid
        #ffmpeg -i /edgefarm_config/Recording/efpg_2023042613_0CH_1st.mp4 -vf "select='eq(n, (v.frames)-1)'" -vframes 1 /edgefarm_config/Recording/efpg_2023042613_0CH_1st.jpg
        # command = f"ffmpeg -i /edgefarm_config/Recording/{max_act_vid} -vf 'select=eq(n), (v.frames)-1)',showinfo -vframes 1 /edgefarm_config/Recording/{img_name}"
        # print(command)ex
        # 입력 비디오 파일 경로
        # input_file = configs.recordinginfo_dir_path + "/" + max_act_vid

        # # 출력 이미지 파일 경로
        # output_file = configs.recordinginfo_dir_path + "/" + img_name

        # # 입력 비디오 파일의 총 프레임 수 계산
        # cmd = "ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 {}".format(input_file)
        # nb_packets = int(subprocess.check_output(cmd, shell=True).decode().strip())
        # nb_frames = nb_packets - 1

        # # FFmpeg를 사용하여 마지막 프레임 추출
        # cmd = "ffmpeg -n  -i {} -vf 'select=eq(n\,{})' -vframes 1 {}".format(input_file, nb_frames, output_file)
        # subprocess.call(cmd, shell=True)

        # subprocess.call(['ffmpeg', '-i', configs.recordinginfo_dir_path+"/"+ max_act_vid, '-vf', 'select=eq(n\,-1)', '-vframes', '1', configs.recordinginfo_dir_path+"/"+img_name])
        # print(['ffmpeg', '-i', configs.recordinginfo_dir_path+"/"+ max_act_vid, '-vf', 'select=eq(n\,-1)', '-vframes', '1', configs.recordinginfo_dir_path+"/"+img_name])
        # result = subprocess.run(command, shell=True)
    # 삭제할 파일 리스트 생성
    # delete_list = [file for file in file_list if file not in max_act_vid_list]
    # # 삭제할 파일 순회하며 삭제
    # for file in delete_list:
    #     file_path = os.path.join(configs.recordinginfo_dir_path, file)
    #     os.remove(file_path)
    return max_act_vid_list 
def clear_orderData():
    # logging.ERROR("클리어 하겠습니다.")  
    try:
        subprocess.run("rm -rf "+configs.METADATA_DIR+"/*", shell=True)
        # subprocess.run("rm -rf "+configs.recordinginfo_dir_path+"/*", shell=True)
    except Exception as e:
        logging.ERROR(f"오류가 발생하였습니다: ",e)     
def matching_cameraId_ch2():
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9))) # 2022-10-21 17:22:32
    now_dt_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_dt_str_for_vid_name = now_dt.strftime("%Y%m%d%H")
    logging.info(now_dt_str_for_vid_name)
    max_act_vid_list=matching_meta_date()
    keys_list = list(max_act_vid_list.keys())
    values_list = list(max_act_vid_list.values())
    print(max_act_vid_list)
    if len(keys_list) >0:
        delete_key_list = [file for file in os.listdir(configs.MetaDate_path) if file not in keys_list ]
        for delete_key in delete_key_list:
            os.remove(os.path.join(configs.MetaDate_path, delete_key))  
        delete_value_list = [file for file in os.listdir(configs.recordinginfo_dir_path) if file not in values_list and 'mp4' in file]
        for delete_value in delete_value_list:
            os.remove(os.path.join(configs.recordinginfo_dir_path, delete_value))  
    for file_name,vid_name in max_act_vid_list.items():
        try:
            # ch_num = int(re.findall(r'\d+', file_name)[0])    
            cam_id=-1
            with open(os.path.join(configs.MetaDate_path, file_name), "r") as json_file:
                content = json.load(json_file)
            if "updated" not in content: # updated 없으면 패스
                logging.info('[updated key가 없어요]')
                logging.info(content)
                continue
            # if content["updated"] == False: # updated False 면 패스
            #     logging.info('[보냈는데 다시 보낼수 없어.]')
            #     logging.info(content)
            #     continue 
            else:
                content.pop('updated') # updated pop     
            content["created_datetime"] = now_dt_str
            if "cam_id" in content:
                cam_id = content.pop('cam_id')
            if "source_id" in content:
                source_id = content.pop('source_id')
            if os.path.isfile(os.path.join(configs.recordinginfo_dir_path, vid_name)):
                if content["weight"] != 0 and content["activity"]>0 and cam_id_info(cam_id,content["activity"]):
                    
                    content['video_path'] = vid_name
                    logging.info("aws s3 cp "+configs.recordinginfo_dir_path+"/"+content['video_path']+" s3://intflow-data/"+str(cam_id)+"/"+content['video_path'])
                    subprocess.run("aws s3 cp "+configs.recordinginfo_dir_path+"/"+content['video_path']+" s3://intflow-data/"+str(cam_id)+"/"+content['video_path'], shell=True)
                else:
                    img_name = os.path.splitext(vid_name)[0]+".jpg"
                    content['thumbnail_path'] = img_name
                    input_file = configs.recordinginfo_dir_path + "/" + vid_name

                    # 출력 이미지 파일 경로
                    output_file = configs.recordinginfo_dir_path + "/" + img_name
                    if not os.path.isfile(os.path.join(configs.recordinginfo_dir_path, output_file)):
                        # 입력 비디오 파일의 총 프레임 수 계산
                        cmd = "ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 {}".format(input_file)
                        nb_packets = int(subprocess.check_output(cmd, shell=True).decode().strip())
                        nb_frames = nb_packets - 1

                        # FFmpeg를 사용하여 마지막 프레임 추출
                        cmd = "ffmpeg -n  -i {} -vf 'select=eq(n\,{})' -vframes 1 {}".format(input_file, nb_frames, output_file)
                        subprocess.call(cmd, shell=True)
                    # #ffmpeg -i input.mp4 -vf "select='eq(n, (v.frames)-1)',showinfo" -vframes 1 output.jpg
                    # command = f"ffmpeg -i {vid_name} -vf 'select=eq(n, (v.frames)-1)',showinfo -vframes 1 {img_name}"
                    # result = subprocess.run(command, shell=True)
                    logging.info("aws s3 cp "+configs.recordinginfo_dir_path+"/"+content['thumbnail_path']+" s3://intflow-data/"+str(cam_id)+"/"+content['thumbnail_path'])
                    subprocess.run("aws s3 cp "+configs.recordinginfo_dir_path+"/"+content['thumbnail_path']+" s3://intflow-data/"+str(cam_id)+"/"+content['thumbnail_path'], shell=True)
            else:
                file_list = os.listdir(configs.recordinginfo_dir_path) 
                for fff in file_list:
                    if now_dt_str_for_vid_name in fff:
                        img_name = os.path.splitext(fff)[0]+".jpg"
                        content['thumbnail_path'] = img_name
                        input_file = configs.recordinginfo_dir_path + "/" + vid_name

                        # 출력 이미지 파일 경로
                        output_file = configs.recordinginfo_dir_path + "/" + img_name
                        if not os.path.isfile(os.path.join(configs.recordinginfo_dir_path, output_file)):
                            # 입력 비디오 파일의 총 프레임 수 계산
                            cmd = "ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 {}".format(input_file)
                            nb_packets = int(subprocess.check_output(cmd, shell=True).decode().strip())
                            nb_frames = nb_packets - 1

                            # FFmpeg를 사용하여 마지막 프레임 추출
                            cmd = "ffmpeg -n  -i {} -vf 'select=eq(n\,{})' -vframes 1 {}".format(input_file, nb_frames, output_file)
                            subprocess.call(cmd, shell=True)
                        # #ffmpeg -i input.mp4 -vf "select='eq(n, (v.frames)-1)',showinfo" -vframes 1 output.jpg
                        # command = f"ffmpeg -i {vid_name} -vf 'select=eq(n, (v.frames)-1)',showinfo -vframes 1 {img_name}"
                        # result = subprocess.run(command, shell=True)
                        logging.info("aws s3 cp "+configs.recordinginfo_dir_path+"/"+content['thumbnail_path']+" s3://intflow-data/"+str(cam_id)+"/"+content['thumbnail_path'])
                        subprocess.run("aws s3 cp "+configs.recordinginfo_dir_path+"/"+content['thumbnail_path']+" s3://intflow-data/"+str(cam_id)+"/"+content['thumbnail_path'], shell=True)
                        break
            
            #if 'thumbnail_path' not in content and 'video_path' not in content:
                #logging.info('thumbnail_path  video_path 없다..')
                    
                # now_dt_str_for_vid_name
            print(content)
            # if content['thumbnail_path']==None and content['video_path']==None:
            #     logging.ERROR("왜 둘다 null이지?") 
            #     content['video_path'] = vid_name
                
            send_meta_api(cam_id, content)
            os.remove(os.path.join(configs.MetaDate_path, file_name))  
        except Exception as e:
                logging.ERROR(f"오류가 발생하였습니다: ",e) 
    if os.path.isfile(os.path.join(configs.local_edgefarm_config_path, "elapsed.txt")):
        os.remove(os.path.join(configs.local_edgefarm_config_path, "elapsed.txt"))    

def grow_sampling_weightlist(answer_count, str_weightlist):
    
    if str_weightlist == "" or answer_count == 0:
        return None, 0, 0
    
    weightlist = [float(x) for x in str_weightlist.split(',')]
    
    avg_wl = sum(weightlist) / len(weightlist)
    std_wl = (sum([((x - avg_wl) ** 2) for x in weightlist]) / len(weightlist)) ** 0.5
    
    normal_weight_vec = []
    result_weight_vec = []
    
    if answer_count > 1:
        limit_alpha = 1
        normal_alpha = 0.68
        
        under_limit_weight, over_limit_weight = avg_wl - limit_alpha * std_wl, avg_wl + limit_alpha * std_wl
        under_normal_weight, over_normal_weight = avg_wl - normal_alpha * std_wl, avg_wl + normal_alpha * std_wl
        
        for w in weightlist:
            if w < under_limit_weight or w > over_limit_weight:
                continue
            elif w < under_normal_weight or w > over_normal_weight:
                result_weight_vec.append(w)
            else:
                normal_weight_vec.append(w)
        
        
        if answer_count - len(result_weight_vec) < 0:
            sp_cnt = answer_count
            
            if len(normal_weight_vec) > 0:
                while True:
                    if sp_cnt < len(normal_weight_vec):
                        # sampling
                        sp_list = random.sample(normal_weight_vec, sp_cnt)
                        result_weight_vec += sp_list
                        break
                    else:
                        sp_cnt -= len(normal_weight_vec)
                        result_weight_vec += normal_weight_vec
                        
            elif len(normal_weight_vec) == 0:
                # 여기 좀 이상함
                sp_list = random.sample(result_weight_vec, sp_cnt)
                result_weight_vec += sp_list
                
        elif answer_count - len(result_weight_vec) > 0:
            sp_cnt = answer_count - len(result_weight_vec)
            
            if sp_cnt == len(normal_weight_vec):
                result_weight_vec += normal_weight_vec
            elif sp_cnt < len(normal_weight_vec):
                sp_list = random.sample(normal_weight_vec, sp_cnt)
                result_weight_vec += sp_list
            else:
                if len(normal_weight_vec) == 0 and len(result_weight_vec) == 0:
                    result_weight_vec = random.sample(weightlist, sp_cnt)
                elif len(normal_weight_vec) == 0 and len(result_weight_vec) != 0:
                    while True:
                        if sp_cnt < len(result_weight_vec):
                            sp_list = random.sample(result_weight_vec, sp_cnt)
                            result_weight_vec += sp_list
                            break
                        else:
                            sp_cnt -= len(result_weight_vec)
                            result_weight_vec += result_weight_vec
                            # C++ code에 추가할 것
                            if sp_cnt == 0:
                                break
                else:
                    while True:
                        if sp_cnt < len(normal_weight_vec):
                            sp_list = random.sample(normal_weight_vec, sp_cnt)
                            result_weight_vec += sp_list
                            break
                        else:
                            sp_cnt -= len(normal_weight_vec)
                            result_weight_vec += normal_weight_vec
    
    elif answer_count == 1:
        result_weight_vec = [avg_wl]
        
    str_result_weightlist = ",".join([f"{x:.2f}" for x in result_weight_vec])
    
    result_avg_weight = sum(result_weight_vec) / len(result_weight_vec)
    result_std_weight = (sum([((x - result_avg_weight) ** 2) for x in result_weight_vec]) / len(result_weight_vec)) ** 0.5
    result_avg_weight=round(result_avg_weight,2)
    # print(f"str : {str_result_weightlist} | avg : {result_avg_weight:.2f} | std : {result_std_weight:.2f}")
    return str_result_weightlist, result_avg_weight, result_std_weight



                
# def matching_cameraId_ch():
#     matching_dic={}
#     matching_meta_date()
#     file_list = os.listdir(configs.recordinginfo_dir_path)
#     now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9))) # 2022-10-21 17:22:32
#     now_dt_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
#     now_dt_str_for_vid_name = now_dt.strftime("%Y%m%d%H")
#     logging.info(now_dt_str_for_vid_name)
#     for file_name in file_list:
#         if "efpg" in file_name and now_dt_str_for_vid_name in file_name:
#             match = re.search(r'(\d+)CH', file_name)
#             logging.info(file_name)
#             if match:
#                 number_str = match.group(1)
#                 number = int(number_str)
#                 with open(os.path.join(configs.roominfo_dir_path+ "/room"+str(number)+".json"), "r") as f:

#                     json_data = json.load(f)
#                 # with open(os.path.join(configs.roominfo_dir_path, "/room"+number+".json", 'r') as f:
#                 #     json_f = json.load(f)
#                 try:
#                     for j_info in json_data["info"]:
#                         cam_id=j_info["id"]
#                         with open(os.path.join(configs.METADATA_DIR, "metadata_grow_"+str(cam_id)+"ch.json"), "r") as json_file:
#                             content = json.load(json_file)
#                             content_og = copy.deepcopy(content)
#                             # cam_id = -1
#                             source_id = -1
#                             if "updated" not in content: # updated 없으면 패스
#                                 logging.info('[updated key가 없어요]')
#                                 logging.info(content)
#                                 continue
#                             if content["updated"] == False: # updated False 면 패스
#                                 logging.info('[보냈는데 다시 보낼수 없어.]')
#                                 logging.info(content)
#                                 continue
#                             else: # updated 있으면
#                                 content.pop('updated') # updated pop
#                                 content_og["updated"] = False # False 로 변경.
#                             # if "created_datetime" not in content:
#                             content["created_datetime"] = now_dt_str
#                             content_og["created_datetime"] = now_dt_str
#                             if "cam_id" in content:
#                                 cam_id = content.pop('cam_id')
#                             if "source_id" in content:
#                                 source_id = content.pop('source_id')
#                             overlay_vid_name = "efpg_" + now_dt_str_for_vid_name + f"_{source_id}CH.mp4"
#                             # cut_video(overlay_vid_name,60)
#                             if content["weight"] != 0 and content["activity"]>0:
#                                 if cam_id_info(cam_id,content["activity"]):
#                                     logging.info("활동량이  "+str(content["activity"])+"kal 이므로"+str(content["activity"])+" 카메라 동영상 보내겠습니다. ")
#                                     content['video_path'] = overlay_vid_name
#                                     # logging.info("aws s3 cp "+configs.recordinginfo_dir_path+"/"+file_name+" s3://intflow-data/"+str(cam_id)+"/"+file_name)
#                                     subprocess.run("aws s3 cp "+configs.recordinginfo_dir_path+"/"+file_name+" s3://intflow-data/"+str(cam_id)+"/"+file_name, shell=True)
#                             # file_name_without_extension = os.path.splitext(overlay_vid_name)[0]
#                             # content['thumbnail_path'] = file_name_without_extension+".jpg"
#                             # thumnail_path = os.path.splitext(configs.recordinginfo_dir_path+"/"+file_name)[0]+'.jpg'
#                             # subprocess.run("aws s3 cp "+thumnail_path+" s3://intflow-data/"+str(cam_id)+"/"+thumnail_path.split('/')[-1], shell=True)
#                             # logging.info("aws s3 cp "+thumnail_path+" s3://intflow-data/"+str(cam_id)+"/"+thumnail_path.split('/')[-1])
#                             if send_meta_api(cam_id, content) == True:
#                                 logging.info('전송.'+str(cam_id))
#                                 os.remove(os.path.join(configs.METADATA_DIR, "metadata_grow_"+str(cam_id)+"ch.json"))
#                             else:
#                                 logging.ERROR('전송 실패.'+str(cam_id))
#                             if content_og is not None:
#                                 with open(os.path.join(configs.METADATA_DIR, "metadata_grow_"+str(cam_id)+"ch.json"), "w") as json_file:
#                                     json.dump(content_og, json_file)
#                         # thumnail_path = os.path.splitext(configs.recordinginfo_dir_path+"/"+file_name)[0]+'.jpg'
#                         # subprocess.run("aws s3 mv "+thumnail_path+" s3://intflow-data/"+str(cam_id)+"/"+thumnail_path.split('/')[-1], shell=True)
#                         # logging.info("aws s3 mv "+thumnail_path+" s3://intflow-data/"+str(cam_id)+"/"+thumnail_path.split('/')[-1])
#                         #         logging.info("aws s3             
#                         # if "efpg" in file_name and now_dt_str_for_vid_name in file_name:
#                         #     # cap = cv2.VideoCapture(configs.recordinginfo_dir_path+"/"+file_name)
#                         #     # # 마지막 프레임 찾기
#                         #     # frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
#                         #     # cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count-1)

#                         #     # # 프레임 읽기
#                         #     # success, image = cap.read()

#                         #     # if success:
#                         #     #     # 이미지 파일로 저장
#                         #     #     cv2.imwrite(thumnail_path, image)
#                         #     try:
#                         #         thumnail_path = os.path.splitext(configs.recordinginfo_dir_path+"/"+file_name)[0]+'.jpg'
#                         #         print(thumnail_path)
#                         #         logging.info('ffmpeg' + '-i '+configs.recordinginfo_dir_path+"/"+ file_name+ '-vf'+ 'select=eq(n\,-1)'+ '-vframes'+ '1'+ configs.recordinginfo_dir_path+"/"+thumnail_path)
#                         #         subprocess.call(['ffmpeg', '-i', configs.recordinginfo_dir_path+"/"+ file_name, '-vf', 'select=eq(n\,-1)', '-vframes', '1', configs.recordinginfo_dir_path+"/"+thumnail_path])
#                         #         subprocess.run("aws s3 mv "+thumnail_path+" s3://intflow-data/"+str(cam_id)+"/"+thumnail_path.split('/')[-1], shell=True)
#                         #         logging.info("aws s3 mv "+thumnail_path+" s3://intflow-data/"+str(cam_id)+"/"+thumnail_path.split('/')[-1])
#                         #     except Exception as e:
#                         #         logging.ERROR("이미지 추출 중 오류가 발생했습니다:", e)
#                     # os.remove(configs.recordinginfo_dir_path+"/"+file_name)
#                 except Exception as e:
#                     logging.ERROR(f"오류가 발생하였습니다: ",e)     
#             subprocess.run("rm -rf "+configs.METADATA_DIR+"/"+"*"+str(cam_id)+"ch.json", shell=True)
    
#         # os.remove(configs.recordinginfo_dir_path+"/"+file_name)
#     # for each_f in os.listdir(configs.roominfo_dir_path):
#     #     if 'room' in each_f:
#     #         room_number=0
#     #         match = re.search(r'room(\d+)', each_f)
#     #         if match:
#     #             number_str = match.group(1)
#     #             room_number = int(number_str)
#     #         json_f = open(os.path.join(configs.roominfo_dir_path, each_f), "r")
#     #         content = json.load(json_f)
#     #         # json_f.close()
#     #         for j_info in content["info"]:
#     #             cam_id=j_info["id"]
#     #             file_list = os.listdir(configs.recordinginfo_dir_path)
#     #             for file_name in file_list:
#     #                 if 'CH' in file_name:
#     #                     match = re.search(r'(\d+)CH', file_name)
#     #                     if match:
#     #                         number_str = match.group(1)
#     #                         number = int(number_str)
#     #                         if =
#     #                         subprocess.run("aws s3 cp "+configs.recordinginfo_dir_path+"/"+file_name+" s3://intflow-data/"+str(cam_id)+"/"+file_name, shell=True)
#     # file_list = os.listdir(configs.recordinginfo_dir_path)
#     # for file_name in file_list:
#     #     if 'CH' in file_name:
#     #         file_ch=file_name.split('CH')[0][-1] 
#     #         if file_ch in matching_dic.keys():
#     #             cam_id=id=matching_dic[file_ch]  
#     #             if now_dt.minute==0 or now_dt.minute>=58:
#     #                 break
#     #             else:
#     #                 subprocess.run("aws s3 mv "+configs.recordinginfo_dir_path+"/"+file_name+" s3://intflow-data/"+str(cam_id)+"/"+file_name, shell=True)
                
# # deepstream 실행 횟수를 체킹하는
def check_deepstream_exec(first_booting):
    logging.info('check_deepstream_exec')
    aws_start=False
    # first_booting=False
    # if first_booting:
        
    #     logging.info('처음시작 실행')
    #     run_SR_docker()
    filesink_braek_num=0
    SR_braek_num=0
    time.sleep(5) # 5초 지연.
    while (True):
        deepstream_exec=False
        SR_exec=False
        aws_exec=False
        now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
        for line in Popen(['ps', 'aux'], shell=False, stdout=PIPE).stdout:
            result = line.decode('utf-8')
            if result.find('deepstream-SR')>1: # deepstream이 ps에 있는지 확인
                SR_exec=True
                logging.info("smart record 실행중")
                filesink_braek_num=0
                SR_braek_num=SR_braek_num+1
                if SR_braek_num>10:
                    logging.info("smart recording (이)가 너무 오래 진행중입니다. 강제 종료 하겠습니다. !")
                    subprocess.run("sudo pkill -9 deepstream-SR", shell=True)  
                break  
            if result.find('deepstream-custom-pipeline')>1 or result.find('deepstream-cust')>1: # deepstream이 ps에 있는지 확인
                deepstream_exec=True
                logging.info("file sink 가 실행중")
                filesink_braek_num=filesink_braek_num+1
                SR_braek_num=0
                if filesink_braek_num>50:
                    logging.info("file sink 가 너무 오래 진행중입니다. 강제 종료 하겠습니다. !")
                    subprocess.run("sudo pkill -9 deepstream-cust", shell=True)   
                break  
            
        if not SR_exec and not deepstream_exec:
            aws_start=run_SR_docker(aws_start)
        # if not deepstream_exec  and now_dt.minute>5: # deepstream이 실행하지 않을때 
        #     with open(configs.deepstream_num_exec, 'r') as f:

        #         json_data = json.load(f)

        #     deepstream_smartrecord = json_data['deepstream_smartrecord']
        #     deepstream_filesink = json_data['deepstream_filesink']
        #     DB_insert = json_data['DB_insert']

        #     if deepstream_smartrecord-1==deepstream_filesink: #스마트레코딩 딥스트립이  파일싱크 딥스트립보다 실행횟수가 많을때 
                
                
        #         logging.info("Smart Recording is over. It's time to run the deepstream file sink.")
        #         run_file_deepstream_docker()
        #     if deepstream_smartrecord==deepstream_filesink and deepstream_filesink-1==DB_insert : #스마트레코딩 딥스트립과 파일싱크 딥스트립보다 실행횟수가 같은데 DB 통신 횟수가 적을때 
                
                
        #         logging.info("deepstream file sink is over. It's time to insert DataBase")
        #         file_list = os.listdir(configs.recordinginfo_dir_path)
        #         now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9))) # 2022-10-21 17:22:32
        #         now_dt_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        #         now_dt_str_for_vid_name = now_dt.strftime("%Y%m%d%H")
        #         logging.info(now_dt_str_for_vid_name)
        #         try:
        #             aws_thread_list = []
        #             aws_thread_mutex = threading.Lock()
        #             aws_thread_cd = threading.Condition()
        #             aws_thread_list.append(threading.Thread(target=matching_cameraId_ch, name="check_deepstream_exec_thread", daemon=True))
        #             aws_thread_list[0].start() 
        #         except Exception as e:
        #             logging.ERROR(e)
        #         json_data['DB_insert']=DB_insert+1  # DB insert count 하나 추가!
        #         with open(configs.deepstream_num_exec, 'w') as f:
        #             json.dump(json_data, f)
        #     if deepstream_smartrecord==deepstream_filesink and deepstream_filesink==DB_insert : #스마트레코딩 딥스트립과 파일싱크 딥스트립, DB 통신 횟수 같을때
                
        #         logging.info('모든 작업이 끝났다. 정각까지 기다리는 시간')
        # if not SR_exec:

        #     if now_dt.minute<=4 :
        #         device_install()
        #         with open(configs.deepstream_num_exec, 'r') as f:

        #             json_data = json.load(f)

        #         deepstream_smartrecord = json_data['deepstream_smartrecord']
        #         deepstream_filesink = json_data['deepstream_filesink']
        #         DB_insert = json_data['DB_insert']                
        #         logging.info("It's time to run Smart Record. ")
        #         if deepstream_smartrecord!=deepstream_filesink:
        #             logging.info("오늘의 스마트레코딩 갯수 과 객체검출 영상 횟수가 같지않음 갯수 조정")
        #             json_data['deepstream_filesink']=deepstream_smartrecord
        #             with open(configs.deepstream_num_exec, 'w') as f:
        #                 json.dump(json_data, f)
        #         if deepstream_smartrecord!=DB_insert:
        #             logging.info("오늘의 스마트레코딩 갯수 과 디비 인설트 횟수가 같지않음 갯수 조정")
        #             json_data['DB_insert']=deepstream_smartrecord
        #             with open(configs.deepstream_num_exec, 'w') as f:
        #                 json.dump(json_data, f)
        #         if deepstream_exec:
        #             logging.info(" file sink가 실행중입니다. 종료하고 스마트레코딩 실행하겠습니다. ")
        #             subprocess.run(f"docker exec -dit {configs.container_name} bash ./kill_filesink.sh", shell=True)     
        #         if aws_exec:
        #             logging.info('시간이 됐다.. aws 강제 종료 ')
        #             subprocess.run("pkill -9 aws", shell=True)     
        #         if deepstream_smartrecord!=deepstream_filesink and deepstream_smartrecord!=DB_insert:
        #             logging.info('루틴 횟수 초기화~')
                    
        #             json_data['deepstream_smartrecord']=0
        #             json_data['DB_insert']=0
        #             json_data['deepstream_filesink']=0
        #             with open(configs.deepstream_num_exec, 'w') as f:
        #                 json.dump(json_data, f)
        #         run_SR_docker()
        time.sleep(10) # 60초 지연.


if __name__ == "__main__":
    # # mac address 뽑기
    # mac_address = getmac.get_mac_address().replace(':','')

    # # device 정보 받기 (api request)
    # device_info = send_api(configs.server_api_path, "48b02d2ecf8c")
    # matching_cameraId_ch()
    # cam_id_info(579,410)
    # run_SR_docker(True)
    matching_cameraId_ch2()
    # matching_meta_date()
    # matching_meta_date()
    # metadata_send_ready()
    # python_log(device_info)
    # model_update_check()
    # device_install()
    # create_food_area()
    # check_deepstream_exec(False)
    # metadata_send()
    # check_aws_install()
