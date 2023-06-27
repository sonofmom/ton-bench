#!/usr/bin/env python3
#
import sys
import os
import argparse
import datetime
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
import Libraries.arguments as ar
import Libraries.tools.general as gt
from Classes.AppConfig import AppConfig
from Classes.TonHttpApi import TonHttpApi
from Classes.Benchmarks.HttpApi.GetTransactionsThread import GetTransactionsThread
from Classes.Benchmarks.HttpApi.ShardsThread import ShardsThread
from Classes.Benchmarks.HttpApi.GetBlockTransactionsThread import GetBlockTransactions
from queue import Queue
import pandas as pd

def run():
    description = 'Executes benchmark of HTTP API instance.'
    parser = argparse.ArgumentParser(formatter_class = argparse.RawDescriptionHelpFormatter,
                                    description = description)

    ar.set_standard_args(parser)
    ar.set_config_args(parser)

    parser.add_argument('-R', '--runtime',
                        required=False,
                        type=int,
                        default=None,
                        dest='max_runtime',
                        action='store',
                        help='Run benchmark for set time in seconds, OPTIONAL, default: unlimited')


    print("Initializing and loading databases, please wait...")
    cfg = AppConfig(parser.parse_args())

    start_timestamp = time.time()
    queues = {}
    th_db = []
    for benchmark, methods in cfg.config["benchmarks"].items():
        queues[benchmark] = {}
        for element in methods:
            e_id = "{}:{}".format(element["method"],element["id"])
            queues[benchmark][e_id] = {
                'success': Queue(),
                'error': Queue()
            }
            cfg.log.log(os.path.basename(__file__), 3, "Configuring benchmark {}:{} with {} thread(s)".format(benchmark,e_id,element["threads"]))
            if element["method"] == 'getTransactions':
                for idx in range(element["threads"]):
                    th_db.append(
                        GetTransactionsThread(
                            id = idx,
                            config=cfg.config,
                            data=cfg.data,
                            log=cfg.log,
                            gk=cfg.gk,
                            queues=queues[benchmark][e_id],
                            params=element["params"],
                            max_rps=element["thread_max_rps"]
                        )
                    )
            elif element["method"] == 'shards':
                for idx in range(element["threads"]):
                    th_db.append(
                        ShardsThread(
                            id = idx,
                            config=cfg.config,
                            data=cfg.data,
                            log=cfg.log,
                            gk=cfg.gk,
                            queues=queues[benchmark][e_id],
                            params=element["params"],
                            max_rps=element["thread_max_rps"]
                        )
                    )
            elif element["method"] == 'getBlockTransactions':
                for idx in range(element["threads"]):
                    th_db.append(
                        GetBlockTransactions(
                            id = idx,
                            config=cfg.config,
                            data=cfg.data,
                            log=cfg.log,
                            gk=cfg.gk,
                            queues=queues[benchmark][e_id],
                            params=element["params"],
                            max_rps=element["thread_max_rps"]
                        )
                    )
            else:
                cfg.log.log(os.path.basename(__file__), 1, "Unknown benchmark method {}:{}".format(benchmark,element["method"]))
                sys.exit(1)

    cfg.log.log(os.path.basename(__file__), 3, "Starting {} threads".format(len(th_db)))
    for element in th_db:
        element.start()

    stats = {
        'start_timestamp': time.time(),
        'threads_count': len(th_db),
        'benchmarks': {},
        'errors': {}
    }
    while True:
        if cfg.gk.kill_now:
            cfg.log.log(os.path.basename(__file__), 3, "Exiting main loop")
            break

        for benchmark in queues.keys():
            if benchmark not in stats['benchmarks']:
                stats['benchmarks'][benchmark] = {}

            for method in queues[benchmark].keys():
                if method not in stats['benchmarks'][benchmark]:
                    stats['benchmarks'][benchmark][method] = {
                        'requests': {
                            'success': 0,
                            'error': 0
                        },
                        'latency': {
                            'min': 9999999,
                            'max': 0,
                            'sum': 0
                        },
                        'errors': {}
                    }

                for idx in range(queues[benchmark][method]['success'].qsize()):
                    result = queues[benchmark][method]['success'].get()
                    stats['benchmarks'][benchmark][method]['requests']['success'] += 1
                    stats['benchmarks'][benchmark][method]['latency']['sum'] += result
                    if result < stats['benchmarks'][benchmark][method]['latency']['min']:
                        stats['benchmarks'][benchmark][method]['latency']['min'] = result
                    elif result > stats['benchmarks'][benchmark][method]['latency']['max']:
                        stats['benchmarks'][benchmark][method]['latency']['max'] = result

                for idx in range(queues[benchmark][method]['error'].qsize()):
                    result = queues[benchmark][method]['error'].get()
                    stats['benchmarks'][benchmark][method]['requests']['error'] += 1
                    if result['error'] not in stats['errors']:
                        stats['errors'][result['error']] = 0

                    stats['errors'][result['error']] +=1

        print_stats(cfg, stats)
        time.sleep(1)
        if cfg.args.max_runtime and (time.time() - stats['start_timestamp']) > cfg.args.max_runtime:
            cfg.gk.kill_now = True

    sys.exit(0)


def print_stats(cfg, stats):
    os.system("clear")
    runtime = round(time.time()-stats['start_timestamp'])
    print("Benchmark Statistics")
    print("-"*100)
    print("Time         : {}".format(time.strftime("%H:%M:%S")))
    if cfg.args.max_runtime:
        print("Runtime      : {} of {} seconds".format(runtime, cfg.args.max_runtime))
    else:
        print("Runtime      : {} seconds".format(runtime))

    print("Total threads: {}".format(stats['threads_count']))

    index = []
    rows = []

    print("-"*100)
    for benchmark, methods in stats['benchmarks'].items():
        for method in methods.keys():
            index.append("{}:{}".format(benchmark, method))
            requests_count = methods[method]['requests']['success'] + methods[method]['requests']['error']
            if requests_count and runtime:
                data = [
                    round(requests_count / runtime, 2),
                    "{}ms / {}ms /{}ms".format(round(methods[method]['latency']['min']),round(methods[method]['latency']['sum']/requests_count),round(methods[method]['latency']['max'])),
                    methods[method]['requests']['success'],
                    methods[method]['requests']['error'],
                    "{}%".format(round((methods[method]['requests']['error'] / requests_count) * 100))
                ]
            else:
                data = [0,0,0,0,0]


            rows.append(data)

    pd.set_option('display.max_rows', 10000)
    table = pd.DataFrame(rows, columns=['RPS', 'Latency', 'Success', 'Failure', 'F.Rate'], index=index)
    print(table)
    print("-"*100)
    print("\n")

    print("Errors")
    print("-"*100)
    if not stats['errors']:
        print("None")
    else:
        index = []
        rows = []
        for error, count in stats['errors'].items():
            index.append(error)
            rows.append([count])

        pd.set_option('display.max_rows', 10000)
        table = pd.DataFrame(rows, columns=['Count'], index=index)
        print(table)

if __name__ == '__main__':
    run()
