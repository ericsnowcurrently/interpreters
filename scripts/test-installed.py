print('importing interpreters')
from interpreters_backport import interpreters
print('importing interpreters.queues')
from interpreters_backport.interpreters import queues
print('importing interpreters.channels')
from interpreters_experimental.interpreters import channels
print('importing concurrent.futures.InterpreterPoolExecutor')
from interpreters_backport.concurrent.futures import InterpreterPoolExecutor


# XXX Actually exercize the modules?
