def matching_cameraId_ch():
    matching_dic={}
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
    file_list = os.listdir(configs.recordinginfo_dir_path)
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9))) # 2022-10-21 17:22:32
    now_dt_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    now_dt_str_for_vid_name = now_dt.strftime("%Y%m%d%H")
    logging.info(now_dt_str_for_vid_name)
    for file_name in file_list:
        match = re.search(r'(\d+)CH', file_name)
        logging.info(file_name)
        if match:
            number_str = match.group(1)
            number = int(number_str)
            with open(os.path.join(configs.roominfo_dir_path+ "/room"+str(number)+".json"), "r") as f:

                json_data = json.load(f)
            # with open(os.path.join(configs.roominfo_dir_path, "/room"+number+".json", 'r') as f:
            #     json_f = json.load(f)
            try:
                for j_info in json_data["info"]:
                    cam_id=j_info["id"]
                    if "efpg" in file_name and now_dt_str_for_vid_name in file_name:
                        # subprocess.run("aws s3 cp "+configs.recordinginfo_dir_path+"/"+file_name+" s3://intflow-data/"+str(cam_id)+"/"+file_name, shell=True)
                        cap = cv2.VideoCapture(configs.recordinginfo_dir_path+"/"+file_name)
                        # 마지막 프레임 찾기
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count-1)

                        # 프레임 읽기
                        success, image = cap.read()

                        if success:
                            # 이미지 파일로 저장
                            thumnail_path = os.path.splitext(configs.recordinginfo_dir_path+"/"+file_name)[0]+'.jpg'
                            cv2.imwrite(thumnail_path, image)
                            logging.info("aws s3 mv "+thumnail_path+" s3://intflow-data/"+str(cam_id)+"/"+thumnail_path.split('/')[-1])
                            subprocess.run("aws s3 mv "+thumnail_path+" s3://intflow-data/"+str(cam_id)+"/"+thumnail_path.split('/')[-1], shell=True)
                    elif "SR_" in file_name:
                        with open('/edgefarm_config/switch_status.txt', 'r') as file:
                            content = file.read()
                        my_bool = bool(int(content)) # True
                        
                        if my_bool:
                            subprocess.run("aws s3 cp "+configs.recordinginfo_dir_path+"/"+file_name+" s3://intflow-data/"+str(cam_id)+"/"+file_name, shell=True)
                            logging.info("aws s3 cp "+configs.recordinginfo_dir_path+"/"+file_name+" s3://intflow-data/"+str(cam_id)+"/"+file_name)
            except Exception as e:
                logging.ERROR(f"오류가 발생하였습니다: ",e)    