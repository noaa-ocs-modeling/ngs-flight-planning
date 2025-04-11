import datetime

class SimpleTimer():
    def __init__(self):
        self.t1 = datetime.datetime.now()
        self.t0 = None

    def update_print(self):
        self.t0 = self.t1
        self.t1 = datetime.datetime.now()
        print(f'{(self.t1 - self.t0)/datetime.timedelta(seconds=1)} s\n')

    def update(self):
        self.t0 = self.t1
        self.t1 = datetime.datetime.now()