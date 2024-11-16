# ton-bench
This repository contains set of scripts that allow benchmarking of ton lite servers / toncenter http api stack.

## How to use
Main script we currently use to test lite-servers is http-api-bench.py, even if we wish to test individual LS we use http-api as middleware for communication as it abstracts many complex queries and frees us from implementing lite-server protocol or forking lite-client binary. Hence ls-bench.py is more of a legacy script for very special use cases.

### System requirements
Benchmark and underlying http api requires considerable ressources to run, you should not run this on the same machine you wish to test as it will have serious impact on the results.

Precise system requirements depend on your situation but we advise to start from 16 core machine to host benchmark + http api service.

### To benchmark http-api endpoint
1) Download and install benchmark code
2) Create benchmark configuration using provided template etc/example_suite.json template.
3) Run http-api-bench.py, see --help for available parameters.

### To benchmark individual lite server
1) Install toncenter http-api (https://github.com/toncenter/ton-http-api) and point it to lite server you wish to test.
2) Download and install benchmark code
3) Create benchmark configuration using provided template etc/example_suite.json template.
4) Run http-api-bench.py, see --help for available parameters.

## Benchmark suite configuration
Each benchmark suite consists of general definitions as well as one or more individual benchmarks, the benchmarks can have different parameters and run simultaniously during suite execution.

### General definitions
#### `data.accounts` and `data.blocks`
Definition of data files to be used lated in individual benchmarks, files are ascii text with one entry per line. In case of addresses each line contains one address, in case of blocks each line contains block definition as: `seqno,workchain,shard`, for example: `40865624,-1,-9223372036854775808`.

To create those files you can use different data sources, for example indexer databases

#### `params.tip_refresh_frequency`
Refresh blockchain tip (load information about MC and WC shards) frequency, in seconds.

### Benchmark definitions
Each benchmark is defined with universal parameters:
* `method`: http-api method to use, currently implemented methods can be seen in Classes/Benchmarks/HttpApi, for example: `shards` or `getTransactions`
* `id`: Free text input, this will be identifier of this particular shard, it will be displayed next to results separated by semicolon from method, for example: `getTransactions:recent`
* `threads`: Number of threads to spawn for this benchmark
* `thread_max_rps`: Maximum RPS allowed for each thread
* `params`: Parameters for benchmark, those depend on method, see further down

Actual RPS load on http-api for each benchmark is `threads` * `thread_max_rps`

#### Method `shards` parameters
##### `seqno_range`
Array with two elemens defining range of masterchain seqnos to randomly run shards query against.
First element can have following values:
* `None`: Use current tip.
* `Integer`: Use defined seqno as range start.
* `Negative Integer`: Use value as offset against blockchain tip seqno.

Second element can have following values:
* `None`: Use current tip.
* `Integer`: Use defined seqno as range end.

For example, definition of [-1000,None] with blockchain tip at 42000000 will take random block between 41999000 and 42000000.

#### Method `getBlockTransactions` parameters
##### `blocks_list`
Identifier of preloaded list of blocks, if set to `None` benchmark will take tip of random workchain currently active in blockchain.

##### `count_range`
Array with two elemens defining range of `count` parameter passed to http api and defining limit of transactions to return for each query.

##### `index_range`
Array with two elemens defining range records to chose from preloaded list of blocks, if such was defined with `blocks_list`, this parameter is ignored if `blocks_list` was set to `None`.

#### Method `getTransactions` parameters
##### `accounts_list`
Identifier of preloaded list of accounts, this parameter is mandatory.

##### `limit_range`
Array with two elemens defining range of `limit` parameter passed to http api and defining limit of transactions to return for each query.

#### Method `getWalletInformation` parameters
##### `accounts_list`
Identifier of preloaded list of accounts, this parameter is mandatory.

## Output and Caveats
Output of benchmark suite includes information on run stats for each benchmark as well as list of errors, if list of errors is large the output might scroll up beyound your terminal screen.

If you encounter this behavior and cannot easily scroll up (tmux or other situation) we advise to use `--render-file` parameter to benchmark script to save the information shown on screen into the file.