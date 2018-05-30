
import datetime


# log generator
class Logger:
    def __init__(self, out):
        self.out = out

    def header(self, string):
        self.out.write("========================================\n")
        self.print("Starting " + string)
        self.out.write("========================================\n")
        self.out.flush()

    @staticmethod
    def msg(string):
        now = datetime.datetime.now()
        return now.strftime('[%Y-%m-%d %H:%M:%S]:') \
            + string + "\n"

    def print(self, string):
        self.out.write(Logger.msg(string))
        self.out.flush()
