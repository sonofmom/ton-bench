from Classes.TonHttpApi import TonHttpApi
from threading import Thread
import time
import random

class ShardsThread(Thread):
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

            tip_seqno = self.data['tip'][-1][0]['seqno']
            if self.params["seqno_range"][0] is None:
                seqno_range_from = tip_seqno
            elif self.params["seqno_range"][0] < 0:
                seqno_range_from = tip_seqno + self.params["seqno_range"][0]
            else:
                seqno_range_from = self.params["seqno_range"][0]

            if self.params["seqno_range"][1] is None:
                seqno_range_to = tip_seqno
            else:
                seqno_range_to = self.params["seqno_range"][1]

            if seqno_range_from == seqno_range_to:
                seqno = seqno_range_from
            else:
                seqno = random.randrange(seqno_range_from,seqno_range_to)

            params = {
                "seqno": seqno
            }
            self.log.log(self.__class__.__name__, 3, '[{}] Requesting shards for seqno {}'.format(self.id,params["seqno"]))
            rs = None
            try:
                rs = self.api.jsonrpc("shards", params)
            except Exception as e:
                self.log.log(self.__class__.__name__, 1, "Query failure: {}".format(str(e)))
                self.queues['error'].put({'request': params, 'error': str(e)})


            runtime_ms = (time.time() - start_timestamp) * 1000
            if not rs:
                self.queues['error'].put({'request': params, 'error': 'Empty response'})
            elif rs["ok"]:
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
