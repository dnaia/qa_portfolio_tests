def clear_metrics(registry):
    with registry._lock:
        for collector in registry._collector_to_names:
            with collector._lock:
                collector._metrics = {}
        registry._names_to_collectors = {}


def get_metric_operations(metric) -> set:
    return set(s.labels['operation'] for s in metric.samples)


def get_sum_values_of_metric(metric, _type: str = '') -> float:
    return sum([s.value for s in metric.samples if s.name.endswith(_type)])
