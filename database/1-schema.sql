CREATE TABLE proxies (
    "proxy_id" SERIAL PRIMARY KEY,
    "address" VARCHAR(40) NOT NULL,
    "port" INT NOT NULL,
    "protocol" VARCHAR(10) DEFAULT 'http',
    CONSTRAINT address_port UNIQUE("address","port")
);

CREATE TABLE proxy_queues (
    "queue_id" SERIAL PRIMARY KEY,
    "domain" VARCHAR(100) NOT NULL,
    CONSTRAINT domain_unique UNIQUE("domain")
);

