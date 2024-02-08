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
from Classes.Benchmarks.HttpApi.GetTransactionsThread import GetTransactionsThread
from Classes.Benchmarks.HttpApi.ShardsThread import ShardsThread
from Classes.Benchmarks.HttpApi.GetBlockTransactionsThread import GetBlockTransactions
from Classes.Benchmarks.HttpApi.GetWalletInformationThread import GetWalletInformationThread
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

    parser.add_argument('-a', '--api-url',
                        required=True,
                        type=str,
                        default=None,
                        dest='api_url',
                        action='store',
                        help='Full URL to http api jsonRPC method, REQUIRED')

    parser.add_argument('-k', '--api-key',
                        required=False,
                        type=str,
                        default=None,
                        dest='api_key',
                        action='store',
                        help='HTTP api key , OPTIONAL')

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
    benchmark_configs = {}
    queues = {}
    th_db = []
    for element in cfg.config["benchmarks"]:
        e_id = "{}:{}".format(element["method"],element["id"])
        benchmark_configs[e_id] = element
        queues[e_id] = {
            'success': Queue(),
            'error': Queue()
        }
        cfg.log.log(os.path.basename(__file__), 3, "Configuring benchmark {} with {} thread(s)".format(e_id,element["threads"]))
        if element["method"] == 'getTransactions':
            for idx in range(element["threads"]):
                th_db.append(
                    GetTransactionsThread(
                        id = idx,
                        config=cfg.config,
                        data=cfg.data,
                        log=cfg.log,
                        gk=cfg.gk,
                        queues=queues[e_id],
                        params=element["params"],
                        max_rps=element["thread_max_rps"]
                    )
                )
        elif element["method"] == 'getWalletInformation':
            for idx in range(element["threads"]):
                th_db.append(
                    GetWalletInformationThread(
                        id = idx,
                        config=cfg.config,
                        data=cfg.data,
                        log=cfg.log,
                        gk=cfg.gk,
                        queues=queues[e_id],
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
                        queues=queues[e_id],
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
                    'config': benchmark_configs[benchmark_id],
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
    print("Remote       : {}".format(cfg.config['http-api']['url']))
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
        requests_rps_target = benchmark_data['config']['threads'] * benchmark_data['config']['thread_max_rps']
        if requests_count and runtime:
            requests_rps = round(requests_count / runtime, 2)
            data = [
                requests_rps_target,
                requests_rps,
                "{}ms".format(round(benchmark_data['latency']['min'])),
                "{}ms".format(round(benchmark_data['latency']['sum']/requests_count)),
                "{}ms".format(round(benchmark_data['latency']['max'])),
                benchmark_data['requests']['success'],
                benchmark_data['requests']['error'],
                "{}%".format(round((benchmark_data['requests']['error'] / requests_count) * 100))
            ]
        else:
            data = [requests_rps_target, 0,"0ms","0ms","0ms",0,0,"0%"]


        rows.append(data)

    pd.set_option('display.max_rows', 10000)
    table = pd.DataFrame(rows, columns=['RPS.T', 'RPS.R', 'L.Min', 'L.Avg','L.Max','Success', 'Failure', 'F.Rate'], index=index)
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

        pd.set_option('display.max_colwidth', 500)
        pd.set_option('display.max_rows', 10000)
        table = pd.DataFrame(rows, columns=['Count'], index=index)
        print(table)

if __name__ == '__main__':
    run()
