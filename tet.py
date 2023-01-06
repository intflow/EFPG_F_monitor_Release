from subprocess import Popen, PIPE
import subprocess
import json
import configs
import os
import re
import datetime as dt
import logging
def remove_SR_vid(debug_print,error_print):
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
    formattedDate = now_dt.strftime("%Y%m%d_%H0000")
    print(formattedDate)
    logger = logging.getLogger(__name__)
    streamHandler = logging.StreamHandler()
    fileHandler = logging.FileHandler('./'+formattedDate+'_monitor.log')
    # formatter 생성
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] >> %(message)s')
    # logger instance에 fomatter 설정
    streamHandler.setFormatter(formatter)
    fileHandler.setFormatter(formatter)

    # logger instance에 handler 설정
    logger.addHandler(streamHandler)
    logger.addHandler(fileHandler)

    # logger instnace로 log 찍기
    logger.setLevel(level=logging.DEBUG)
    if debug_print!='':
        logger.debug(debug_print)
    # logger.info('my INFO log')
    # logger.warning('my WARNING log')
    if error_print!='':
        logger.error(error_print)
    # logger.critical('my CRITICAL log')
        
    
    
if __name__ == "__main__":
    # handler 생성 (stream, file)
    remove_SR_vid('dddd','')
    
    
