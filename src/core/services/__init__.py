"""
core.services package

Esse __init__.py existe para garantir que `src.core.services` seja um pacote
"normal", permitindo que o pytest monkeypatch resolva caminhos do tipo:
`src.core.services.clientes_service.update_cliente`.
"""
