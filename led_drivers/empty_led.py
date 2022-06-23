class LED:
    def __init__(self, port) -> None:
        print("LED open: ", port)
    def setCurrent(self, i):
        print("LED current: ",i)
    def disconnect(self):
        print("LED switched off")