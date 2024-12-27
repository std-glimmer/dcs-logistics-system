class LoggerService:
    def __init__(self, log_file='logs/app.log'):
        self.log_file = log_file

    def log(self, message, level='INFO'):
        log_message = f"{level}: {message}"
        print(log_message)
        with open(self.log_file, 'a') as f:
            f.write(log_message + '\n')

    def info(self, message):
        self.log(message, level='INFO')

    def warning(self, message):
        self.log(message, level='WARNING')

    def error(self, message):
        self.log(message, level='ERROR')