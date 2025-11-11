"""
Teste para verificar a busca case/accent-insensitive de clientes.

Testa:
1. Normalização com _normalize() remove acentos
2. Busca por "Ocimar" ou "Ósimar" funciona
3. Busca por CNPJ sem formatação funciona
"""
import unicodedata
import re


def _normalize(s: str) -> str:
    """Normaliza texto para busca (remove acentos, casefold, só alfanum)."""
    s = s or ""
    # Remove acentos (decomposição Unicode)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    # casefold() é mais robusto que lower() para comparações i18n
    s = s.casefold()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def test_normalize():
    """Testa normalização de texto."""
    # Acentos
    assert _normalize("Ósimar") == "osimar"
    assert _normalize("José") == "jose"
    assert _normalize("María") == "maria"
    
    # Case-insensitive
    assert _normalize("OCIMAR") == "ocimar"
    assert _normalize("Ocimar") == "ocimar"
    assert _normalize("ocimar") == "ocimar"
    
    # Múltiplas palavras
    assert _normalize("João da Silva") == "joao da silva"
    assert _normalize("MARIA JOSÉ") == "maria jose"
    
    # CNPJ (mantém números)
    assert _normalize("12.345.678/0001-90") == "12 345 678 0001 90"
    
    print("✅ Todos os testes de normalização passaram!")


def test_search_simulation():
    """Simula busca de clientes."""
    # Base de dados simulada
    clientes = [
        {"razao_social": "Ocimar e Cia Ltda", "cnpj": "12.345.678/0001-90", "nome": "Ocimar Silva"},
        {"razao_social": "José Transportes", "cnpj": "98.765.432/0001-11", "nome": "José Santos"},
        {"razao_social": "Maria Comércio", "cnpj": "11.222.333/0001-44", "nome": "Maria Costa"},
    ]
    
    # Busca por "ocimar" (minúscula)
    query = _normalize("ocimar")
    print(f"  Query normalizada: '{query}'")
    results = []
    for c in clientes:
        hay = " ".join([
            str(c.get("razao_social") or ""),
            str(c.get("nome") or ""),
            str(c.get("cnpj") or ""),
        ])
        hay_norm = _normalize(hay)
        print(f"  Comparando com: '{hay_norm[:50]}...'")
        if query in hay_norm:
            results.append(c)
    
    print(f"  Resultados: {len(results)}")
    assert len(results) == 1, f"Esperado 1, encontrado {len(results)}"
    assert results[0]["razao_social"] == "Ocimar e Cia Ltda"
    print(f"✅ Busca por 'ocimar' encontrou: {results[0]['razao_social']}")
    
    # Busca por "OCIMAR" (maiúscula)
    query = _normalize("OCIMAR")
    results = []
    for c in clientes:
        hay = " ".join([
            str(c.get("razao_social") or ""),
            str(c.get("nome") or ""),
            str(c.get("cnpj") or ""),
        ])
        hay_norm = _normalize(hay)
        if query in hay_norm:
            results.append(c)
    
    assert len(results) == 1
    assert results[0]["razao_social"] == "Ocimar e Cia Ltda"
    print(f"✅ Busca por 'OCIMAR' encontrou: {results[0]['razao_social']}")
    
    # Busca por "José" (com acento)
    query = _normalize("José")
    results = []
    for c in clientes:
        hay = " ".join([
            str(c.get("razao_social") or ""),
            str(c.get("nome") or ""),
            str(c.get("cnpj") or ""),
        ])
        hay_norm = _normalize(hay)
        if query in hay_norm:
            results.append(c)
    
    assert len(results) == 1
    assert results[0]["razao_social"] == "José Transportes"
    print(f"✅ Busca por 'José' encontrou: {results[0]['razao_social']}")
    
    # Busca por "jose" (sem acento)
    query = _normalize("jose")
    results = []
    for c in clientes:
        hay = " ".join([
            str(c.get("razao_social") or ""),
            str(c.get("nome") or ""),
            str(c.get("cnpj") or ""),
        ])
        hay_norm = _normalize(hay)
        if query in hay_norm:
            results.append(c)
    
    assert len(results) == 1
    assert results[0]["razao_social"] == "José Transportes"
    print(f"✅ Busca por 'jose' (sem acento) encontrou: {results[0]['razao_social']}")
    
    # Busca por CNPJ (só números)
    # No app real, o CNPJ é buscado removendo todos os não-dígitos
    query = "12345678"  # busca sem normalização para números
    results = []
    for c in clientes:
        cnpj_limpo = re.sub(r"\D+", "", c.get("cnpj") or "")
        if query in cnpj_limpo:
            results.append(c)
    
    assert len(results) == 1
    assert results[0]["cnpj"] == "12.345.678/0001-90"
    print(f"✅ Busca por CNPJ '12345678' encontrou: {results[0]['razao_social']}")
    
    # Busca alternativa: pelo campo normalizado
    query = _normalize("12.345.678/0001-90")
    results = []
    for c in clientes:
        hay = " ".join([
            str(c.get("razao_social") or ""),
            str(c.get("nome") or ""),
            str(c.get("cnpj") or ""),
        ])
        hay_norm = _normalize(hay)
        # Busca com tokens
        tokens = query.split()
        if all(t in hay_norm for t in tokens):
            results.append(c)
    
    assert len(results) == 1
    print(f"✅ Busca por CNPJ completo encontrou: {results[0]['razao_social']}")


if __name__ == "__main__":
    print("=" * 60)
    print("TESTE: Busca Case/Accent-Insensitive")
    print("=" * 60)
    print()
    
    test_normalize()
    print()
    test_search_simulation()
    print()
    print("=" * 60)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("=" * 60)
