import datetime as dt
import time
while(True):
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
    print(now_dt.minute)
    time.sleep(600)