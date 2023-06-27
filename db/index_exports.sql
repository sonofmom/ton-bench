/* Export Accounts */
copy (select distinct account from transactions) To '/tmp/accounts.txt' with csv delimiter ',';

/* Export Blocks */
copy (select seqno, workchain, shard from blocks where workchain = -1 order by seqno) To '/tmp/blocks_mc.txt' with csv delimiter ',';
copy (select seqno, workchain, shard from blocks where workchain = 0 order by seqno) To '/tmp/blocks_wc.txt' with csv delimiter ',';
