#!/usr/bin/env python2

import logging

# set log to console
log_level = logging.DEBUG
log_formatter = logging.Formatter('%(asctime)s : %(levelname)10s : %(message)s')

log = logging.getLogger('my_log')
log.setLevel(log_level)

console_log = logging.StreamHandler()
console_log.setFormatter(log_formatter)

log.addHandler(console_log)


log.debug('debug message')
log.info('info message')
log.warn('warn message')
log.error('error message')
log.critical('critical message')


file_log = logging.FileHandler('my_log_file.txt', mode='w')
file_log.setFormatter(log_formatter)

log.addHandler(file_log)



log.debug('debug message')
log.info('info message')
log.warn('warn message')
log.error('error message')
log.critical('critical message')
