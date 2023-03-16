FAN_SPEED = 150

API_HOST = "http://intflowserver2.iptime.org:20052"

# API_HOST2 = "http://intflowserver2.iptime.org:20051"
API_HOST2 = "http://intflowserver2.iptime.org:60080"
METADATA_DIR = "/edgefarm_config/metadata"

docker_repo = "intflow/efpg_f"
docker_image_tag_header_list = ["dev", "res"] # res 우선
docker_image_tag_header = "None" # Don't Touch!! 수정하지 말고 놔두기!! 자동으로 잡음.

local_edgefarm_config_path = "/edgefarm_config"
edgefarm_config_path = "/edgefarm_config/edgefarm_config.json"
edgefarm_port_info_path = "/edgefarm_config/port_info.txt"
container_name = "efhall_test"
roominfo_dir_path = "/edgefarm_config/roominfo"
recordinginfo_dir_path = "/edgefarm_config/Recording"
DB_datetime=""
MetaDate_path="/edgefarm_config/metadata/"
edgefarm_config_json_path = "/edgefarm_config/edgefarm_config.json"
model_export_container_name = "export_model"
server_bucket_of_model = "intflow-models"
server_model_file_name = "intflow_model.onnx"
local_model_file_relative_path = "model/intflow_model.onnx"
commit_container_name = "for_commit"
deepstream_num_exec="/edgefarm_config/deepstream_num_of_exec.json"
firmware_dir = "/home/intflow/works/firmwares/"
key_match_dict = {
    'device_id' : 'id',
    'auto_mode' : 'auto_mode_status',
    'auto_stop_second' : 'auto_interval'
}

MUST_copy_edgefarm_config_list=[]
not_copy_DB_config_list=[]

server_api_path = "/device/info"
access_api_path = "/device/access"
last_ip = None

docker_id = None
docker_pw = None

log_save_dir_path_host = "/home/intflow/works/logs/"
log_save_dir_path_docker = "/works/logs/"
log_max_volume = 536870912 # bytes 단위 3달은 버팀.
# log_max_volume = 200000 # bytes 단위 3달은 버팀.

update_hour, update_min, update_sec = [23,50,0]

internet_ON = False