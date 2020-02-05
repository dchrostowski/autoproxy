CREATE TABLE proxies (
    "proxy_id" SERIAL PRIMARY KEY,
    "address" VARCHAR(40) NOT NULL,
    "port" INT NOT NULL,
    "protocol" VARCHAR(10) DEFAULT 'http',
    CONSTRAINT address_port_unique UNIQUE("address","port")
);

CREATE TABLE queues (
    "queue_id" SERIAL PRIMARY KEY,
    "domain" VARCHAR(100) NOT NULL,
    CONSTRAINT domain_unique UNIQUE("domain")
);

CREATE TABLE details (
    "detail_id" SERIAL PRIMARY KEY,
    "proxy_id" INTEGER REFERENCES proxies("proxy_id") NOT NULL,
    "queue_id" INTEGER REFERENCES queues("queue_id") NOT NULL,
    "active" BOOLEAN DEFAULT false,
    "load_time" INT DEFAULT 60000,
    "last_updated" TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    "last_active" TIMESTAMP DEFAULT '2000-01-01',
    "last_used" TIMESTAMP DEFAULT '2000-01-01',
    "bad_count" INT DEFAULT 0,
    "blacklisted" BOOLEAN DEFAULT false,
    "blacklisted_count" INTEGER DEFAULT 0,
    "lifetime_good" INTEGER DEFAULT 0,
    "lifetime_bad" INTEGER DEFAULT 0,
    CONSTRAINT proxy_queue_unique UNIQUE("proxy_id","queue_id")
    
);
