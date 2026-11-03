"""Failures remain pending; a retry reuses an already committed classification."""

from dataclasses import dataclass


@dataclass
class RunStats:
    delivered: int = 0
    suppressed: int = 0
    failed: int = 0


def process_pending(store, classifier, sink, limit=100):
    stats = RunStats()
    for row in store.pending(sink.destination, limit):
        post, result = store.decode(row)
        if result is None:
            try:
                # Validate even custom classifiers; no adapter bypasses the shared contract.
                from .domain import Classification

                result = Classification.validate(classifier.classify(post).to_dict(), post)
                store.save_result(post.key, result, classifier.name)
            except Exception:
                store.classification_failed(post.key, "classification_failed")
                stats.failed += 1
                continue
        if not result.alertable:
            store.delivery(post.key, sink.destination, "suppressed")
            stats.suppressed += 1
            continue
        store.delivery(post.key, sink.destination, "pending")
        try:
            sink.send(post, result)
        except Exception:
            # Do not store provider exceptions: they can contain tokens, URLs, or content.
            store.delivery(post.key, sink.destination, "pending", "delivery_failed", attempted=True)
            stats.failed += 1
        else:
            store.delivery(post.key, sink.destination, "delivered", attempted=True)
            stats.delivered += 1
    return stats
