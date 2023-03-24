# # mac address 뽑기
# mac_address = getmac.get_mac_address().replace(':','')

# # device 정보 받기 (api request)
# device_info = send_api(configs.server_api_path, mac_address)

#%%

## 임의 device_info 생성
device_info_example = {
    "rtsp_address": "file:///works/videos/15fps_3min_1ch.mp4",
    "vpi_k1": -0.00026,
    "vpi_k2": 0.0,
    "x_focus": 0,
    "x_pad": 0.0,
    "x_rotate": 0.0,
    "x_scale": 1.0,
    "y_focus": 0,
    "y_pad": 0.8,
    "y_rotate": 0.0,
    "y_scale": 1.0,
    "zx_perspect": -0.0,
    "zy_perspect": 0.007,
    "grow_width_cm": 10.0,
    "grow_width_pixel": 10,
    "weight_bias": 0.0,
    "limit_min_weight": 0.0,
    "limit_max_weight": 160.0  
}

device_info = {}
for i in range(8):
    device_info[i+1] = device_info_example
    device_info[i+1]["rtsp_address"] = f"file:///works/videos/15fps_3min_{i+1}ch.mp4"

import shutil
import os
import json

roominfo_dir_path = "/edgefarm_config/roominfo"

#%%

# roominfo 디렉토리 삭제 및 재생성
if os.path.isdir(roominfo_dir_path):
    shutil.rmtree(roominfo_dir_path)
os.mkdir(roominfo_dir_path)

#%%
# room json 파일 생성
cnt = 0
for k, v in device_info.items():
    # print(k, v)
    each_info = {"cam_id" : k}
    each_info.update(v)
    
    with open(os.path.join(roominfo_dir_path, f"room{cnt}.json"), "w") as json_f:
        json.dump(each_info, json_f, indent=4)
    
    cnt += 1
    
#%%
for each_f in os.listdir(roominfo_dir_path):
    json_f = open(os.path.join(roominfo_dir_path, each_f), "r")
    content = json.load(json_f)
    json_f.close()
    content["cam_id"] = -1
    json_f = open(os.path.join(roominfo_dir_path, each_f), "w")
    json.dump(content, json_f, indent=4)
    json_f.close()

#%%

if device_info is not None:
    print(device_info)

    # roominfo 디렉토리 삭제 및 재생성
    shutil.rmtree(roominfo_dir_path)

    # file read
    with open(configs.edgefarm_config_path, "r") as edgefarm_config_file:
        edgefarm_config = json.load(edgefarm_config_file)

    for key, val in edgefarm_config.items():
        if key in device_info:
            print(f'{key} : {val} -> {device_info[key]}')
            edgefarm_config[key] = device_info[key]
        else:
            key_match(key, edgefarm_config, device_info)

    # file save
    with open(configs.edgefarm_config_path, "w") as edgefarm_config_file:
        json.dump(edgefarm_config, edgefarm_config_file, indent=4)

    # rtsp address set
    if 'default_rtsp' in device_info:
        rtsp_src_address = device_info['default_rtsp']
        print(f"\nRTSP source address : {rtsp_src_address}\n")
        if rtsp_src_address is not None:
            with open('/edgefarm_config/rtsp_address.txt', 'w') as rtsp_src_addr_file:
                rtsp_src_addr_file.write(rtsp_src_address)

else:
    print("device_info is None!")
    # file read
    with open(configs.edgefarm_config_path, "r") as edgefarm_config_file:
        edgefarm_config = json.load(edgefarm_config_file)
    
    edgefarm_config["device_id"] = -1
    edgefarm_config["auto_mode"] = False
        
    # file save
    with open(configs.edgefarm_config_path, "w") as edgefarm_config_file:
        json.dump(edgefarm_config, edgefarm_config_file, indent=4)