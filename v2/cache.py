"""A scalar, single-head causal attention example with actual prefix KV reuse."""
import math

def attend(tokens, past=()):
    kv = list(past)
    for token in tokens:
        x = (sum(map(ord, token)) % 19) / 19
        kv.append((0.6*x, 0.9*x))
        weights = [math.exp(x*k) for k, _ in kv]
        output = sum(w*v for w, (_, v) in zip(weights, kv)) / sum(weights)
    return kv, output

def experiment():
    prefix = "review the checkout incident using the approved operations runbook".split()
    suffix = ["again"]
    cold, y1 = attend(prefix + suffix)
    warm, _ = attend(prefix)
    _, y2 = attend(suffix, warm)
    return {"prefix_tokens":len(prefix), "cold_projections":len(cold),
            "warm_projections":len(suffix), "same_output":math.isclose(y1,y2)}
