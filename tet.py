import logging
import traceback
import datetime as dt


def main():
    print("TEST")
    # test() 

def python_log(print_log):
    now_dt = dt.datetime.now().astimezone(dt.timezone(dt.timedelta(hours=9)))
    formattedDate = now_dt.strftime("%Y%m%d_%H0000")
    f = open(formattedDate+"log.log", "a", encoding="UTF8")
    f.write(print_log+'\n')
    f.close()
if __name__ == '__main__':
    python_log('슈ㄹ')
