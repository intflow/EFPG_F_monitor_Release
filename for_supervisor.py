from concurrent.futures import thread
import os
import re
import datetime as dt
import subprocess
import time
import requests
import json
import getmac
import threading
import multiprocessing
import configs
from utils import *
import logging
import traceback
import firmwares_manager
    
def key_match(src_key, src_data, target_data):
    if src_key in configs.key_match_dict:
        target_key = configs.key_match_dict[src_key]
        if target_key in target_data:
            target_val = target_data[target_key]
            print(f"{src_key} : {src_data[src_key]} -> {target_val}")
            src_data[src_key] = target_val 

# folder scale check
def get_dir_size(path='.'):
    total = 0
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += get_dir_size(entry.path)
    return total

def get_size(path='.'):
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        return get_dir_size(path)

def folder_value_check(_time, _path_, ALLOW_CAPACITY, BOOL_HOUR_CHECK, FIRST_BOOT_REMOVER = False):
    
    if FIRST_BOOT_REMOVER:
        try: # 이 자리에 시간마다 처리하고 싶은 코드를 집어 넣으면 됨.
            # folder_scale = get_size(_path_) / (1024.0 * 1024.0 * 1000.0)
            diskInfo  = os.statvfs('/')
            used      = diskInfo.f_bsize * (diskInfo.f_blocks - diskInfo.f_bavail) / (1024.0 * 1024.0 * 1000.0)
            free      = diskInfo.f_bsize * diskInfo.f_bavail / (1024.0 * 1024.0 * 1000.0)
            total     = diskInfo.f_bsize * diskInfo.f_blocks / (1024.0 * 1024.0 * 1000.0)
            print(f"used : {used} | free : {free} | total : {total}")
            if free < total * ALLOW_CAPACITY_RATE:
                max_day_cnt = 30
                while (max_day_cnt >= -1):
                    
                    # folder 내부 날짜순으로 제거
                    os.system(f"sudo find {_path_} -name '*.mp4' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    os.system(f"sudo find {_path_} -name '*.jpeg' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    os.system(f"sudo find {_path_} -name '*.jpg' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    # command = f"find {_path_} -type f -ctime +{max_day_cnt}" + " -exec rm -rf {} \;"
                    
                    # folder 크기 확인
                    # folder_scale = get_size(_path_) / (1024.0 * 1024.0 * 1000.0)
                    
                    diskInfo  = os.statvfs('/')
                    free      = diskInfo.f_bsize * diskInfo.f_bavail / (1024.0 * 1024.0 * 1000.0)
                    
                    if free > ALLOW_CAPACITY:
                        print(f"After remove file : {free:.2f} GB")
                        break
                    
                    max_day_cnt -= 1
                    
        except Exception as e: # 에러 출력
            print(e) 
    
    if _time.minute == 0 and _time.second < 5 and BOOL_HOUR_CHECK == False:
            
        try: # 이 자리에 시간마다 처리하고 싶은 코드를 집어 넣으면 됨.
            # folder_scale = get_size(_path_) / (1024.0 * 1024.0 * 1000.0)
            _path_ = re.sub("\n", "", _path_)
            diskInfo  = os.statvfs(_path_)
            used      = diskInfo.f_bsize * (diskInfo.f_blocks - diskInfo.f_bavail) / (1024.0 * 1024.0 * 1000.0)
            free      = diskInfo.f_bsize * diskInfo.f_bavail / (1024.0 * 1024.0 * 1000.0)
            total     = diskInfo.f_bsize * diskInfo.f_blocks / (1024.0 * 1024.0 * 1000.0)
            
            print(f"use : {used:.2f} | free : {free:.2f} | total : {total:.2f}")
            os.system(f"sudo find {_path_} -name '*.mp4'")
            
            if free < total * ALLOW_CAPACITY_RATE:
                max_day_cnt = 30
                while (max_day_cnt >= -1):
                    
                    # folder 내부 날짜순으로 제거
                    os.system(f"sudo find {_path_} -name '*.mp4' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    os.system(f"sudo find {_path_} -name '*.jpeg' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    os.system(f"sudo find {_path_} -name '*.jpg' -ctime +{max_day_cnt}" + " -exec rm -rf {} \;")
                    # command = f"find {_path_} -type f -ctime +{max_day_cnt}" + " -exec rm -rf {} \;"
                    
                    # folder 크기 확인
                    # folder_scale = get_size(_path_) / (1024.0 * 1024.0 * 1000.0)
                    
                    diskInfo  = os.statvfs(_path_)
                    free      = diskInfo.f_bsize * diskInfo.f_bavail / (1024.0 * 1024.0 * 1000.0)
                    
                    if free > total * ALLOW_CAPACITY_RATE:
                        print(f"After remove file : {free:.2f} GB")
                        break
                    
                    max_day_cnt -= 1
                    
        except Exception as e: # 에러 출력
            print(e) 
            
        if BOOL_HOUR_CHECK == False:
            BOOL_HOUR_CHECK = True
    
    elif _time.minute == 0 and _time.second > 5 and BOOL_HOUR_CHECK == True:
        BOOL_HOUR_CHECK = False
        
    return BOOL_HOUR_CHECK

# class TestThread1(threading.Trhead):
#     def __init__(self):
#         threading.Thread.__init__(self, daemon=True)
#     def run(self):
        

if __name__ == "__main__":
    try:
        max_power_mode()
        configs.internet_ON = internet_check()    
        fan_speed_set(configs.FAN_SPEED)
        KST_timezone_set()
        
        first_booting=False
        docker_repo = configs.docker_repo
        docker_image, docker_image_id = find_lastest_docker_image(docker_repo)
        docker_image_tag_header = configs.docker_image_tag_header
        
        os.makedirs(configs.firmware_dir, exist_ok=True)
        firmwares_manager.copy_firmwares()
        
        device_install()
        # check_aws_install()
        # model_update_check() #모델 export하는 코드 일단 막아놈
        
        # metadata 권한 변경.
        subprocess.run(f"sudo chown intflow:intflow -R {configs.METADATA_DIR}", shell=True)
        subprocess.run(f"sudo chmod 775 -R {configs.METADATA_DIR}", shell=True)
        now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
        print(now_dt.hour)
        
        # subprocess.run("sudo shutdown -r 23:55", shell=True)
        #sudo shutdown -r 22:00
        
        clear_deepstream_exec()
        
        # 폴더 자동삭제를 위한 설정
        f = open("/edgefarm_config/Smart_Record.txt","rt")
        _ = f.readline()
        _path_ = f.readline()
        f.close()
        print(f"[Info] target video folder : {_path_}")
        # _path_ = '/edgefarm_config/Recording' # folder path를 변수로 입력
        # ALLOW_CAPACITY = 100 # 단위 : gb, 폴더 허용 최대크기
        ALLOW_CAPACITY_RATE = 0.02 # 단위 : rate, 폴더 저장 MAX percent
        BOOL_HOUR_CHECK = False # 한시간 마다 체크, 시간 상태 처리를 한번만 할 때 유용함
        LOG_DIR_CHECK = False
        
        # ! 맨 처음 실행했을 떄 한번 체크하게 설정
        _time = dt.datetime.now()
        folder_value_check(_time, _path_, ALLOW_CAPACITY_RATE, BOOL_HOUR_CHECK, FIRST_BOOT_REMOVER = True)
        # python_log('check_deepstream_exec')
        deepstreamCheck_thread_list = []
        deepstreamCheck_thread_mutex = threading.Lock()
        deepstreamCheck_thread_cd = threading.Condition()
        # deepstreamCheck_thread = threading.Thread(target=check_deepstream_exec, name="check_deepstream_exec_thread", args=(first_booting,))
        # deepstreamCheck_thread.start()
        deepstreamCheck_thread_list.append(threading.Thread(target=check_deepstream_exec, name="check_deepstream_exec_thread", daemon=True, args=(first_booting,)))
        deepstreamCheck_thread_list[0].start()

        # edgefarm 구동.
        while (True):
            
            if check_deepstream_status():
                # print("here")
                pass
            else:
                try:
                    # docker 실행과 동시에 edgefarm 실행됨.
                    docker_image, docker_image_id = find_lastest_docker_image(docker_repo)
                    run_docker(docker_image, docker_image_id)
                    
                    # deepstreamCheck_thread_mutex = threading.Lock()
                    # deepstreamCheck_thread_cd = threading.Condition()
                    # deepstreamCheck_thread = threading.Thread(target=check_deepstream_exec,args=(first_booting,))
                    # deepstreamCheck_thread.start()
                    # if deepstreamCheck_thread
                    
                    # 쓰레드 죽었는지 검사해서 죽으면 다시 실행
                    if deepstreamCheck_thread_list[0].is_alive() == False:
                        deepstreamCheck_thread_list.clear()
                        deepstreamCheck_thread_list.append(threading.Thread(target=check_deepstream_exec, name="check_deepstream_exec_thread", daemon=True, args=(first_booting,)))
                        deepstreamCheck_thread_list[0].start()            
                        # python_log('check_deepstream_exec')
                    first_booting=False
                except Exception as e:
                    python_log(e)
            try:
                # 동영상 폴더 제거 알고리즘
                _time = dt.datetime.now()
                BOOL_HOUR_CHECK = folder_value_check(_time, _path_, ALLOW_CAPACITY_RATE, BOOL_HOUR_CHECK)
                LOG_DIR_CHECK = log_dir_vol_manage(_time, LOG_DIR_CHECK)
                
                # git pull
                firmwares_manager.git_pull()
                
            except Exception as e:
                python_log(e)

            time.sleep(0.5) # 1초 지연.

        print("\nEdgefarm End...\n")
    except:
        logging.basicConfig(filename='../logs/ERROR.log', level=logging.ERROR)
        now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
        formattedDate = now_dt.strftime("%Y%m%d_%H%M%S")
        logging.error('['+str(formattedDate)+']'+traceback.format_exc())
        # python_log('에러발생!!!! ERROR.log에 log저장 .  3분뒤 재부팅 , 재부팅을 원하지 않으면 sudo shutdown -c 를 입력하시오')
        # subprocess.run("sudo shutdown -r +3", shell=True)
        

