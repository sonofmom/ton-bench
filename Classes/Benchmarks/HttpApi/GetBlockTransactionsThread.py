import Libraries.tools.general as gt
from Classes.TonHttpApi import TonHttpApi
from threading import Thread
import time
import random

class GetBlockTransactions(Thread):
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
        if self.params["index_range"][1] is None:
            self.params["index_range"][1] = len(self.data["blocks"][self.params["blocks_list"]])-1

        while True:
            if self.gk.kill_now:
                self.log.log(self.__class__.__name__, 3, '[{}] Terminating'.format(self.id))
                return

            start_timestamp = time.time()

            block = self.data["blocks"][self.params["blocks_list"]][random.randrange(self.params["index_range"][0],self.params["index_range"][1])]
            if (self.params["count_range"][0] == self.params["count_range"][1]):
                count = self.params["count_range"][0]
            else:
                count = random.randrange(self.params["count_range"][0],self.params["count_range"][1])

            params = {
                "seqno": block[0],
                "workchain": block[1],
                "shard": block[2],
                "count": count
            }
            self.log.log(self.__class__.__name__, 3, '[{}] Requesting {} transactions for block {}:{}:{}'.format(self.id,params["seqno"],params["count"],params["seqno"],params["workchain"],params["shard"]))
            rs = None
            try:
                rs = self.api.jsonrpc("getBlockTransactions", params)
            except Exception as e:
                self.log.log(self.__class__.__name__, 1, "Query failure: {}".format(str(e)))
                self.queues['error'].put({'request': params, 'error': str(e)})


            runtime_ms = (time.time() - start_timestamp) * 1000
            if not rs:
                self.queues['error'].put({'request': params, 'error': 'Empty response'})
            if rs["ok"]:
                self.log.log(self.__class__.__name__, 3, '[{}] Query completed in {} ms'.format(self.id,runtime_ms))
                self.queues['success'].put(runtime_ms)
            else:
                self.log.log(self.__class__.__name__, 3, '[{}] Query failed in {} ms'.format(self.id,runtime_ms))
                self.queues['error'].put({'request': params, 'error': rs["error"]})

            if (runtime_ms < self.min_runtime_ms):
                sleep_ms = self.min_runtime_ms - runtime_ms
                self.log.log(self.__class__.__name__, 3, '[{}] Sleeping for {} ms'.format(self.id,sleep_ms))
                time.sleep(sleep_ms/1000)

# end class
