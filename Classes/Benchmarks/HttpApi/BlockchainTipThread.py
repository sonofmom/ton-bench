from Classes.TonHttpApi import TonHttpApi
from threading import Thread
import time
import random

class BlockchainTipThread(Thread):
    def __init__(self, config, log=None, data=None, gk=None, refresh_frequency=1):
        Thread.__init__(self)
        self.config = config
        self.log = log
        self.data = data
        self.gk = gk
        self.frequency_ms = refresh_frequency*1000
        self.api = TonHttpApi(self.config["http-api"],self.log)

    def run(self):
        while True:
            if self.gk.kill_now:
                self.log.log(self.__class__.__name__, 3, 'Terminating')
                return

            start_timestamp = time.time()
            result = {}
            last_mc_seqno=None
            shards=None
            try:
                rs = self.api.jsonrpc("getMasterchainInfo", {})
                last_mc_seqno = rs["result"]["last"]["seqno"]
            except Exception as e:
                self.log.log(self.__class__.__name__, 1, "Query failure: {}".format(str(e)))
                last_mc_seqno=None

            if last_mc_seqno:
                result = {
                    -1: [
                        {
                            'seqno': last_mc_seqno,
                            'shard': -9223372036854775808
                        }
                    ]
                }
                params = {
                    "seqno": last_mc_seqno
                }
                self.log.log(self.__class__.__name__, 3, 'Requesting shards for seqno {}'.format(params["seqno"]))
                try:
                    rs = self.api.jsonrpc("shards", params)
                    if rs:
                        shards = rs["result"]["shards"]
                except Exception as e:
                    self.log.log(self.__class__.__name__, 1, "Query failure: {}".format(str(e)))

            if shards:
                for element in shards:
                    if element['workchain'] not in result:
                        result[element['workchain']] = []

                    result[element['workchain']].append(
                        {
                            'seqno': element['seqno'],
                            'shard': element['shard']
                        }
                    )

                self.data['tip'] = result

            runtime_ms = (time.time() - start_timestamp) * 1000
            if (runtime_ms < self.frequency_ms):
                sleep_ms = self.frequency_ms - runtime_ms
                self.log.log(self.__class__.__name__, 3, 'Sleeping for {} ms'.format(sleep_ms))
                time.sleep(sleep_ms/1000)

# end class
