/* Export ALL Accounts */
copy (select distinct account from transactions) To '/tmp/accounts.txt' with csv delimiter ',';

/* Export Accounts active in last 24 Hours */
copy (select
          distinct account
      from
          transactions
      where
          utime >  (EXTRACT(EPOCH FROM NOW()) - 86400)::BIGINT
    ) To '/tmp/accounts_recent.txt' with csv delimiter ',';

/* Export top 8192 accounts active in last 24 Hours */
copy (WITH top_accounts AS (
    SELECT count(*), account
    FROM transactions
    WHERE utime > (EXTRACT(EPOCH FROM NOW()) - 86400)::BIGINT
    GROUP BY account
    ORDER BY count desc
    LIMIT 8192
)
SELECT account
FROM top_accounts) To '/tmp/accounts_top_recent.txt' with csv delimiter ',';

/* Export Blocks */
copy (select seqno, workchain, shard from blocks where workchain = -1 order by seqno) To '/tmp/blocks_mc.txt' with csv delimiter ',';
copy (select seqno, workchain, shard from blocks where workchain = 0 order by seqno) To '/tmp/blocks_wc.txt' with csv delimiter ',';

/* Export masterchain blocks for last 24 Hours */
copy (select
          blocks.seqno,
          blocks.workchain,
          blocks.shard
      from
          blocks,
          block_headers
      where
          blocks.block_id = block_headers.block_id
        and blocks.workchain = -1
        and block_headers.gen_utime > (EXTRACT(EPOCH FROM NOW()) - 86400)::BIGINT
      order by blocks.workchain, blocks.shard, blocks.seqno) To '/tmp/blocks_mc_recent.txt' with csv delimiter ',';

/* Export workchain blocks for last 24 Hours */
copy (select
          blocks.seqno,
          blocks.workchain,
          blocks.shard
      from
          blocks,
          block_headers
      where
          blocks.block_id = block_headers.block_id
        and blocks.workchain = 0
        and block_headers.gen_utime > (EXTRACT(EPOCH FROM NOW()) - 86400)::BIGINT
      order by blocks.workchain, blocks.shard, blocks.seqno) To '/tmp/blocks_wc_recent.txt' with csv delimiter ',';

/* Export accounts active during tonano storm in december 2023 */
copy (select
          distinct account
      from
          transactions
      where
          utime > 1702288800
        and utime < 1702893600
          ) To '/tmp/accounts_tonano.txt' with csv delimiter ',';


/* Export Blocks during tonano inscriptions storm in december 2023 */
copy (select
          blocks.seqno,
          blocks.workchain,
          blocks.shard
      from
          blocks,
          block_headers
      where
          blocks.block_id = block_headers.block_id
        and block_headers.gen_utime > 1702288800
        and block_headers.gen_utime < 1702893600
      order by blocks.workchain, blocks.shard, blocks.seqno) To '/tmp/blocks_tonano.txt' with csv delimiter ',';

