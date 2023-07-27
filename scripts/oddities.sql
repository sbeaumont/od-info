select
    target, target_name, count(1) as bounced
from
    TownCrier
where
    event_type = 'bounce'
group by
    target
order by
    bounced desc;

select
    origin_name, count(1) as bouncer
from
    TownCrier
where
    event_type = 'bounce'
group by
    origin
order by
    bouncer desc;

select origin, target, event_type, text
from TownCrier
where
    (event_type = 'bounce') and
    ((origin = 10717) or
    (target = 10717));

select
    origin,
    origin_name,
    count(1) as declarations
from TownCrier
where
    event_type like 'war_declare'
group by
    origin
order by
    declarations desc;

select
    target,
    target_name,
    count(1) as declared_on
from TownCrier
where
    event_type like 'war_declare'
group by
    target
order by
    declared_on desc;

select
    target_name as dominion,
    sum(amount) as total,
    count(1) as hits
from
    TownCrier
group by
    target
order by
    total desc;

select
    target_name as dominion,
    sum(amount) as total,
    count(1) as hits
from
    TownCrier
group by
    target
order by
    total desc;

select
    origin_name as dominion,
    sum(amount) as total,
    count(1) as hits
from
    TownCrier
group by
    origin
order by
    total desc;