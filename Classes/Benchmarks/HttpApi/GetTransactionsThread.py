from Classes.TonHttpApi import TonHttpApi
from threading import Thread
import time
import random

class GetTransactionsThread(Thread):
    def __init__(self, id, config, data=None, log=None, queues=None, gk=None, params=None, max_rps=1):
        Thread.__init__(self)
        self.id = id
        self.config = config
        self.log = log
        self.data = data
        self.queues = queues
        self.gk = gk
        self.params = params
        self.min_runtime_ms = (1 / max_rps) * 1000
        self.api = TonHttpApi(self.config["http-api"],self.log)

    def run(self):
        while True:
            if self.gk.kill_now:
                self.log.log(self.__class__.__name__, 3, '[{}] Terminating'.format(self.id))
                return

            start_timestamp = time.time()

            address = self.data["accounts"][self.params["accounts_list"]][random.randrange(len(self.data["accounts"][self.params["accounts_list"]]))]
            params = {
                "address": address,
                "limit": random.randrange(self.params["limit_range"][0],self.params["limit_range"][1])
            }
            self.log.log(self.__class__.__name__, 3, '[{}] Requesting {} transactions for address {}'.format(self.id,params["limit"],params["address"]))
            rs = None
            try:
                rs = self.api.jsonrpc("getTransactions", params)
                runtime_ms = (time.time() - start_timestamp) * 1000
                if not rs:
                    self.queues['error'].put({'request': params, 'error': 'Empty response'})
                elif rs["ok"]:
                    self.log.log(self.__class__.__name__, 3, '[{}] Query completed in {} ms'.format(self.id,runtime_ms))
                    self.queues['success'].put(runtime_ms)
                else:
                    self.log.log(self.__class__.__name__, 3, '[{}] Query failed in {} ms'.format(self.id,runtime_ms))
                    self.queues['error'].put({'request': params, 'error': rs["error"]})
            except Exception as e:
                runtime_ms = (time.time() - start_timestamp) * 1000
                self.log.log(self.__class__.__name__, 1, "Query failure: {}".format(str(e)))
                self.queues['error'].put({'request': params, 'error': str(e)})


            if (runtime_ms < self.min_runtime_ms):
                sleep_ms = self.min_runtime_ms - runtime_ms
                self.log.log(self.__class__.__name__, 3, '[{}] Sleeping for {} ms'.format(self.id,sleep_ms))
                time.sleep(sleep_ms/1000)

# end class
