select p.protocol, p.address, p.port, q.domain, d.lifetime_good, d.lifetime_bad, d.last_active, d.last_used,  d.load_time, d.blacklisted from details d join proxies p on p.proxy_id = d.proxy_id join queues q on q.queue_id = d.queue_id order by d.lifetime_good desc limit 20;

