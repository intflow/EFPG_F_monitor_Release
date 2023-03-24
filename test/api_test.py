import subprocess
import requests
import getmac
import json

# cancel
# put /report/auto/cancel/{report_id}

def cancel_api(report_id):
    API_HOST = "http://intflow.serveftp.com:8737"
    url = API_HOST + '/report/auto/cancel/' + str(report_id)

    print(url)

    try:
        response = requests.put(url)

        print("response status : %r" % response.status_code)
        return response.json()
    except Exception as ex:
        print(ex)
        return None
    

def send_api(path, mac_address):
    API_HOST = "http://intflow.serveftp.com:1151"
    url = API_HOST + path + '/' + mac_address

    print(url)
    
    try:
        response = requests.put(url)

        print("response status : %r" % response.status_code)
        return response.json()
    except Exception as ex:
        print(ex)
        return None

def key_match(key_match_dict, src_key, src_data, target_data):
    target_key = key_match_dict[src_key]
    if src_key in key_match_dict and target_key in target_data:
        target_val = target_data[target_key]
        print(f"{src_key} : {src_data[src_key]} -> {target_val}")
        src_data[src_key] = target_val 

def device_install(edgefarm_config_path):
    # mac address 뽑기
    mac_address = getmac.get_mac_address().replace(':','')

    # device 정보 받기 (api request)
    device_info = send_api("/device/install", mac_address)
    
    key_match_dict = {
        'device_id' : 'id',
        'auto_mode' : 'auto_mode_status',
        'auto_stop_second' : 'auto_interval'
    }

    if device_info is not None:
        print(device_info)

        # file read
        with open(edgefarm_config_path, "r") as edgefarm_config_file:
            edgefarm_config = json.load(edgefarm_config_file)

        for key, val in edgefarm_config.items():
            if key in device_info:
                print(f'{key} : {val} -> {device_info[key]}')
                edgefarm_config[key] = device_info[key]
            else:
                key_match(key_match_dict, key, edgefarm_config, device_info)
                # if key == 'device_id' and 'id' in device_info:
                #     print(f"{key} : {val} -> {device_info['id']}")
                #     edgefarm_config[key] = device_info['id']
                # elif key == 'auto_mode' and 'auto_mode_status' in device_info:
                #     print(f"{key} : {val} -> {device_info['auto_mode_status']}")
                #     edgefarm_config[key] = device_info['auto_mode_status']
                # elif key == 'auto_stop_second' and 'auto_interval' in device_info:
                #     print(f"{key} : {val} -> {device_info['auto_interval']}")
                #     edgefarm_config[key] = device_info['auto_interval']

        # file save
        with open(edgefarm_config_path, "w") as edgefarm_config_file:
            json.dump(edgefarm_config, edgefarm_config_file, indent=4)

        # # rtsp address set
        # if 'default_rtsp' in device_info:
        #     rtsp_src_address = device_info['default_rtsp']
        #     print(f"\nRTSP source address : {rtsp_src_address}\n")
        #     if rtsp_src_address is not None:
        #         with open('/edgefarm_config/rtsp_address.txt', 'w') as rtsp_src_addr_file:
        #             rtsp_src_addr_file.write(rtsp_src_address)

    else:
        print("device_info is None!")
        # file read
        with open(edgefarm_config_path, "r") as edgefarm_config_file:
            edgefarm_config = json.load(edgefarm_config_file)
        
        edgefarm_config["device_id"] = -1
        edgefarm_config["auto_mode"] = False
            
        # file save
        with open(edgefarm_config_path, "w") as edgefarm_config_file:
            json.dump(edgefarm_config, edgefarm_config_file, indent=4)        
    
if __name__ == "__main__":
    # edgefarm_config_path = "./edgefarm_config/edgefarm_config.json"
    # device_install(edgefarm_config_path)
    
    print(cancel_api(6196))
        
        
    # test_a = 1        
    # td1()

    # print(test_a)
    
    # print(port_status_check(8100))
    
    # try:
    #     subprocess.check_output("netstat -ltu | grep {}".format(8102), shell=True)
    # except subprocess.CalledProcessError:
    #     print("no")
    # subprocess.run("netstat -ltu | grep {}".format(8102), shell=True, check=True, stdout=subprocess.PIPE).stdout
    
    # print(autorun_service_check())
    
    # port_process_kill(8101)
    
    # print(type(12) == int)
    
    