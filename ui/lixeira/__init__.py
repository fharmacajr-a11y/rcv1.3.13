
# Export preguiçoso para evitar import circular
def abrir_lixeira(*args, **kwargs):
    from .lixeira import abrir_lixeira as _abrir
    return _abrir(*args, **kwargs)

__all__ = ["abrir_lixeira"]
