select q.domain, count(*) as c from details d join queues q on q.queue_id = d.queue_id where d.active = True group by q.domain order by c desc;
