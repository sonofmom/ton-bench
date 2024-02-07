from Classes.LiteClient import LiteClient
from threading import Thread
import time
import random

class GetAccountThread(Thread):
    def __init__(self, id, config, ls_addr, ls_key, data=None, log=None, queues=None, gk=None, params=None, max_rps=1):
        Thread.__init__(self)
        self.id = id
        self.config = config
        self.log = log
        self.data = data
        self.queues = queues
        self.gk = gk
        self.params = params
        self.min_runtime_ms = (1 / max_rps) * 1000
        self.lc = LiteClient(args=[],
                             config=self.config['liteClient'],
                             ls_addr=ls_addr,
                             ls_key=ls_key,
                             log=self.log)

    def run(self):
        while True:
            if self.gk.kill_now:
                self.log.log(self.__class__.__name__, 3, '[{}] Terminating'.format(self.id))
                return

            start_timestamp = time.time()

            query = "getaccount {}".format(self.data["accounts"][self.params["accounts_list"]][random.randrange(len(self.data["accounts"][self.params["accounts_list"]]))])
            self.log.log(self.__class__.__name__, 3, '[{}] Query {}'.format(self.id,query))
            rs=None
            try:
                rs = self.lc.exec(query, nothrow=True)
                runtime_ms = (time.time() - start_timestamp) * 1000
                if not rs:
                    self.queues['error'].put({'request': query, 'error': 'Empty response'})
                if rs.find("account balance is"):
                    self.log.log(self.__class__.__name__, 3, '[{}] Query completed in {} ms'.format(self.id,runtime_ms))
                    self.queues['success'].put(runtime_ms)
                else:
                    self.log.log(self.__class__.__name__, 3, '[{}] Query failed in {} ms'.format(self.id,runtime_ms))
                    self.queues['error'].put({'request': query, 'error': 'Invalid response'})

            except Exception as e:
                runtime_ms = (time.time() - start_timestamp) * 1000
                self.log.log(self.__class__.__name__, 1, "Query failure: {}".format(str(e)))
                self.queues['error'].put({'request': query, 'error': str(e)})

            if (runtime_ms < self.min_runtime_ms):
                sleep_ms = self.min_runtime_ms - runtime_ms
                self.log.log(self.__class__.__name__, 3, '[{}] Sleeping for {} ms'.format(self.id,sleep_ms))
                time.sleep(sleep_ms/1000)

# end class
