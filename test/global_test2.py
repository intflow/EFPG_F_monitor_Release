def test_def2(test_str):
    # global test_str
    print(f"test_str : Bye")
    test_str[0] = "Bye"
    
def test_def1(control_thread_cd):
    print('해제!')
    with control_thread_cd:
        control_thread_cd.notifyAll()