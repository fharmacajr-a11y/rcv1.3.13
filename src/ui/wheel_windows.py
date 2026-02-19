# Windows-only wheel normalizer
def wheel_steps(event) -> int:
    d = int(getattr(event, "delta", 0))  # múltiplos de 120 no Windows
    if d == 0:
        return 0
    step = d // 120
    return step if step != 0 else (1 if d > 0 else -1)
