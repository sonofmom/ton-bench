#!/usr/bin/env python3
#
import sys
import os
import argparse
import time
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from Classes.AppConfig import AppConfig
from Classes.Benchmarks.LiteServer.GetAccountThread import GetAccountThread
from Classes.Benchmarks.HttpApi.ShardsThread import ShardsThread
from Classes.Benchmarks.HttpApi.GetBlockTransactionsThread import GetBlockTransactions
from queue import Queue
import pandas as pd

def run():
    description = 'Executes benchmark of HTTP API instance.'
    parser = argparse.ArgumentParser(formatter_class = argparse.RawDescriptionHelpFormatter,
                                    description = description)

    parser.add_argument('-b', '--benchmark',
                        required=True,
                        type=str,
                        default=None,
                        dest='benchmark',
                        action='store',
                        help='Benchmark definition json file, REQUIRED')

    parser.add_argument('-a', '--addr',
                        required=True,
                        type=str,
                        dest='ls_addr',
                        action='store',
                        help='LiteServer address:port - REQUIRED')

    parser.add_argument('-B', '--b64',
                        required=True,
                        type=str,
                        dest='ls_key',
                        action='store',
                        help='LiteServer base64 key as encoded in network config - REQUIRED')

    parser.add_argument('-R', '--runtime',
                        required=False,
                        type=int,
                        default=None,
                        dest='max_runtime',
                        action='store',
                        help='Run benchmark for set time in seconds, OPTIONAL, default: unlimited')

    parser.add_argument('-v', '--verbosity',
                        required=False,
                        type=int,
                        default=0,
                        dest='verbosity',
                        action='store',
                        help='Verbosity 0 - 3 - OPTIONAL, default: 0')

    print("Initializing and loading databases, please wait...")
    cfg = AppConfig(parser.parse_args())

    start_timestamp = time.time()
    queues = {}
    th_db = []
    for element in cfg.config["benchmarks"]:
        e_id = "{}:{}".format(element["method"],element["id"])
        queues[e_id] = {
            'success': Queue(),
            'error': Queue()
        }
        cfg.log.log(os.path.basename(__file__), 3, "Configuring benchmark {} with {} thread(s)".format(e_id,element["threads"]))
        if element["method"] == 'getAccount':
            for idx in range(element["threads"]):
                th_db.append(
                    GetAccountThread(
                        id = idx,
                        config=cfg.config,
                        ls_addr=cfg.args.ls_addr,
                        ls_key=cfg.args.ls_key,
                        data=cfg.data,
                        log=cfg.log,
                        gk=cfg.gk,
                        queues=queues[e_id],
                        params=element["params"],
                        max_rps=element["thread_max_rps"]
                    )
                )
        else:
            cfg.log.log(os.path.basename(__file__), 1, "Unknown benchmark method {}".format(element["method"]))
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

        for benchmark_id, benchmark_queues in queues.items():
            if benchmark_id not in stats['benchmarks']:
                stats['benchmarks'][benchmark_id] = {
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

            for idx in range(benchmark_queues['success'].qsize()):
                result = benchmark_queues['success'].get()
                stats['benchmarks'][benchmark_id]['requests']['success'] += 1
                stats['benchmarks'][benchmark_id]['latency']['sum'] += result
                if result < stats['benchmarks'][benchmark_id]['latency']['min']:
                    stats['benchmarks'][benchmark_id]['latency']['min'] = result
                elif result > stats['benchmarks'][benchmark_id]['latency']['max']:
                    stats['benchmarks'][benchmark_id]['latency']['max'] = result

            for idx in range(benchmark_queues['error'].qsize()):
                result = benchmark_queues['error'].get()
                stats['benchmarks'][benchmark_id]['requests']['error'] += 1
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
    print("Remote       : {}".format(cfg.args.ls_addr))
    print("Start Time   : {}".format(datetime.fromtimestamp(stats['start_timestamp'], tz=ZoneInfo("UTC"))))
    print("Current Time : {}".format(datetime.now(tz=ZoneInfo("UTC"))))
    if cfg.args.max_runtime:
        print("Runtime      : {} of {} seconds".format(runtime, cfg.args.max_runtime))
    else:
        print("Runtime      : {} seconds".format(runtime))

    print("Total threads: {}".format(stats['threads_count']))

    index = []
    rows = []

    print("-"*100)
    for benchmark_id, benchmark_data in stats['benchmarks'].items():
        index.append("{}".format(benchmark_id))
        requests_count = benchmark_data['requests']['success'] + benchmark_data['requests']['error']
        if requests_count and runtime:
            data = [
                round(requests_count / runtime, 2),
                "{}ms".format(round(benchmark_data['latency']['min'])),
                "{}ms".format(round(benchmark_data['latency']['sum']/requests_count)),
                "{}ms".format(round(benchmark_data['latency']['max'])),
                benchmark_data['requests']['success'],
                benchmark_data['requests']['error'],
                "{}%".format(round((benchmark_data['requests']['error'] / requests_count) * 100))
            ]
        else:
            data = [0,"0ms","0ms","0ms",0,0,"0%"]


        rows.append(data)

    pd.set_option('display.max_rows', 10000)
    table = pd.DataFrame(rows, columns=['RPS', 'L.Min', 'L.Avg','L.Max','Success', 'Failure', 'F.Rate'], index=index)
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
