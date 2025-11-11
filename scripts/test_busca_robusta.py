"""
Teste da busca robusta por Razão Social, Nome do Contato e CNPJ (com/sem máscara).

Valida:
1. Busca por razão social (case/accent-insensitive)
2. Busca por nome de contato em campos variados
3. Busca por CNPJ com máscara (07.816.095/0001-65)
4. Busca por CNPJ sem máscara (07816095000165)
"""
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Importa os helpers de busca
from src.modules.auditoria.view import (
    _norm_text,
    _digits,
    _collect_name_like_fields,
    _build_search_index,
)


def test_norm_text():
    """Testa normalização de texto."""
    print("\n=== Teste: _norm_text() ===")

    # Acentos
    assert _norm_text("Ósimar") == "osimar"
    print("✓ 'Ósimar' → 'osimar'")

    assert _norm_text("José") == "jose"
    print("✓ 'José' → 'jose'")

    assert _norm_text("María") == "maria"
    print("✓ 'María' → 'maria'")

    # Case-insensitive
    assert _norm_text("AMAFARMA") == "amafarma"
    print("✓ 'AMAFARMA' → 'amafarma'")

    assert _norm_text("Ocimar Silva") == "ocimar silva"
    print("✓ 'Ocimar Silva' → 'ocimar silva'")

    # None-safe
    assert _norm_text(None) == ""
    print("✓ None → ''")

    print("✅ Todos os testes de _norm_text() passaram!\n")


def test_digits():
    """Testa extração de dígitos."""
    print("=== Teste: _digits() ===")

    # CNPJ com máscara
    assert _digits("07.816.095/0001-65") == "07816095000165"
    print("✓ '07.816.095/0001-65' → '07816095000165'")

    assert _digits("12.345.678/0001-90") == "12345678000190"
    print("✓ '12.345.678/0001-90' → '12345678000190'")

    # Telefones
    assert _digits("(11) 98765-4321") == "11987654321"
    print("✓ '(11) 98765-4321' → '11987654321'")

    # None-safe
    assert _digits(None) == ""
    print("✓ None → ''")

    # Já sem máscara
    assert _digits("07816095000165") == "07816095000165"
    print("✓ '07816095000165' → '07816095000165'")

    print("✅ Todos os testes de _digits() passaram!\n")


def test_collect_name_like_fields():
    """Testa coleta de campos de nomes."""
    print("=== Teste: _collect_name_like_fields() ===")

    # Cliente com múltiplos campos de nome
    cliente = {
        "razao_social": "AMAFARMA LTDA",
        "cnpj": "07.816.095/0001-65",
        "nome": "Ocimar",
        "contato": "João Silva",
        "responsavel": "Maria Santos",
        "telefone": "(11) 98765-4321",
    }

    nomes = _collect_name_like_fields(cliente)
    print(f"✓ Nomes encontrados: {nomes}")

    assert "Ocimar" in nomes
    assert "João Silva" in nomes
    assert "Maria Santos" in nomes
    print("✓ Campos 'nome', 'contato', 'responsavel' detectados")

    # Deve ignorar campos não relacionados a nomes
    assert "AMAFARMA LTDA" not in nomes  # razão social não é nome de pessoa
    assert "(11) 98765-4321" not in nomes  # telefone não é nome
    print("✓ Campos não relacionados ignorados")

    print("✅ Todos os testes de _collect_name_like_fields() passaram!\n")


def test_build_search_index():
    """Testa construção do índice de busca."""
    print("=== Teste: _build_search_index() ===")

    cliente = {
        "razao_social": "AMAFARMA LTDA",
        "cnpj": "07.816.095/0001-65",
        "nome": "Ocimar Silva",
        "contato": "João Santos",
    }

    idx = _build_search_index(cliente)

    # Razão social normalizada
    assert idx["razao"] == "amafarma ltda"
    print(f"✓ razao: '{idx['razao']}'")

    # CNPJ sem máscara
    assert idx["cnpj"] == "07816095000165"
    print(f"✓ cnpj: '{idx['cnpj']}'")

    # Nomes normalizados
    assert "ocimar silva" in idx["nomes"]
    assert "joao santos" in idx["nomes"]
    print(f"✓ nomes: {idx['nomes']}")

    print("✅ Todos os testes de _build_search_index() passaram!\n")


def test_search_simulation():
    """Simula busca real de clientes."""
    print("=== Teste: Simulação de Busca ===")

    # Base de dados simulada
    clientes = [
        {
            "id": 1,
            "razao_social": "AMAFARMA LTDA",
            "cnpj": "07.816.095/0001-65",
            "nome": "Ocimar Silva",
            "contato": "João Santos",
        },
        {
            "id": 2,
            "razao_social": "JOSÉ TRANSPORTES",
            "cnpj": "12.345.678/0001-90",
            "nome": "José Santos",
        },
        {
            "id": 3,
            "razao_social": "MARIA COMÉRCIO",
            "cnpj": "98.765.432/0001-11",
            "nome": "Maria Costa",
        },
    ]

    # Teste 1: Busca por razão social (case-insensitive)
    print("\n1. Busca por 'amafarma':")
    query = "amafarma"
    q_text = _norm_text(query)
    results = [c for c in clientes if q_text in _build_search_index(c)["razao"]]
    assert len(results) == 1
    assert results[0]["razao_social"] == "AMAFARMA LTDA"
    print(f"   ✓ Encontrado: {results[0]['razao_social']}")

    # Teste 2: Busca por nome de contato
    print("\n2. Busca por 'ocimar' (nome de contato):")
    query = "ocimar"
    q_text = _norm_text(query)
    results = []
    for c in clientes:
        idx = _build_search_index(c)
        if any(q_text in nome for nome in idx["nomes"]):
            results.append(c)
    assert len(results) == 1
    assert results[0]["nome"] == "Ocimar Silva"
    print(f"   ✓ Encontrado: {results[0]['razao_social']} (contato: {results[0]['nome']})")

    # Teste 3: Busca por CNPJ COM máscara
    print("\n3. Busca por '07.816.095/0001-65' (CNPJ com máscara):")
    query = "07.816.095/0001-65"
    q_digits = _digits(query)
    results = [c for c in clientes if q_digits in _build_search_index(c)["cnpj"]]
    assert len(results) == 1
    assert results[0]["cnpj"] == "07.816.095/0001-65"
    print(f"   ✓ Encontrado: {results[0]['razao_social']} ({results[0]['cnpj']})")

    # Teste 4: Busca por CNPJ SEM máscara
    print("\n4. Busca por '07816095000165' (CNPJ sem máscara):")
    query = "07816095000165"
    q_digits = _digits(query)
    results = [c for c in clientes if q_digits in _build_search_index(c)["cnpj"]]
    assert len(results) == 1
    assert results[0]["cnpj"] == "07.816.095/0001-65"
    print(f"   ✓ Encontrado: {results[0]['razao_social']} ({results[0]['cnpj']})")

    # Teste 5: Busca por parte do CNPJ
    print("\n5. Busca por '07816095' (parte do CNPJ):")
    query = "07816095"
    q_digits = _digits(query)
    results = [c for c in clientes if q_digits in _build_search_index(c)["cnpj"]]
    assert len(results) == 1
    print(f"   ✓ Encontrado: {results[0]['razao_social']}")

    # Teste 6: Busca com acentos
    print("\n6. Busca por 'José' (com acento):")
    query = "josé"
    q_text = _norm_text(query)
    results = []
    for c in clientes:
        idx = _build_search_index(c)
        if q_text in idx["razao"] or any(q_text in nome for nome in idx["nomes"]):
            results.append(c)
    assert len(results) == 1
    assert results[0]["razao_social"] == "JOSÉ TRANSPORTES"
    print(f"   ✓ Encontrado: {results[0]['razao_social']}")

    print("\n✅ Todos os testes de simulação passaram!\n")


if __name__ == "__main__":
    print("=" * 70)
    print("TESTE: Busca Robusta (Razão + Contato + CNPJ)")
    print("=" * 70)

    test_norm_text()
    test_digits()
    test_collect_name_like_fields()
    test_build_search_index()
    test_search_simulation()

    print("=" * 70)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 70)
    print("\nBusca validada para:")
    print("  • Razão Social (case/accent-insensitive)")
    print("  • Nome do Contato (em campos variados)")
    print("  • CNPJ com máscara (07.816.095/0001-65)")
    print("  • CNPJ sem máscara (07816095000165)")
    print("  • Busca parcial por CNPJ")
