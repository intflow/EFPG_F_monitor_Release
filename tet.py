import logging
import traceback

logging.basicConfig(filename='./test.log', level=logging.ERROR)

def main():
    print("TEST")
    test() 

if __name__ == '__main__':
    try:
        main()
    except:
        logging.error(traceback.format_exc())