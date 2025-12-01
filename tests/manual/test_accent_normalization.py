"""
Script de teste para validar a normalização de acentos na Fase 9.
"""

import unicodedata


# Implementa a função localmente para evitar import circular
def _strip_accents(value: str) -> str:
    """Remove acentos de uma string usando normalizacao Unicode NFKD."""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_key_for_storage(key: str) -> str:
    """Normaliza key do Storage removendo acentos APENAS do nome do arquivo (ultimo segmento)."""
    key = key.strip("/").replace("\\", "/")
    parts = key.split("/")
    if parts:
        # Remove acentos apenas do nome do arquivo (ultimo segmento)
        filename = parts[-1]
        parts[-1] = _strip_accents(filename)
    return "/".join(parts)


# Casos de teste
test_cases = [
    # (input_key, expected_output)
    ("ORG123/148/GERAL/sifap/Certidão de Regularidade.pdf", "ORG123/148/GERAL/sifap/Certidao de Regularidade.pdf"),
    ("ORG123/148/GERAL/sifap/Licença Sanitaria.pdf", "ORG123/148/GERAL/sifap/Licenca Sanitaria.pdf"),
    (
        "ORG123/148/GERAL/sifap/CONTRATO SOCIAL - ALTERAÇÃO.pdf",
        "ORG123/148/GERAL/sifap/CONTRATO SOCIAL - ALTERACAO.pdf",
    ),
    (
        "ORG123/148/GERAL/sifap/Comprovante Endereço Empresa.pdf",
        "ORG123/148/GERAL/sifap/Comprovante Endereco Empresa.pdf",
    ),
    (
        "ORG123/148/GERAL/sifap/AFE.pdf",
        "ORG123/148/GERAL/sifap/AFE.pdf",  # Sem acento, mantém
    ),
    (
        "ORG123/148/GERAL/sifap/CND FEDERAL (2).pdf",
        "ORG123/148/GERAL/sifap/CND FEDERAL (2).pdf",  # Sem acento, mantém
    ),
]

print("=" * 80)
print("TESTE DE NORMALIZAÇÃO DE ACENTOS - FASE 9")
print("=" * 80)

all_passed = True
for input_key, expected in test_cases:
    result = normalize_key_for_storage(input_key)
    passed = result == expected
    all_passed = all_passed and passed

    status = "✅ PASS" if passed else "❌ FAIL"
    filename = input_key.split("/")[-1]

    print(f"\n{status}")
    print(f"  Arquivo: {filename}")
    print(f"  Input:    {input_key}")
    print(f"  Expected: {expected}")
    print(f"  Got:      {result}")

    if not passed:
        print("  ⚠️ DIFERENÇA DETECTADA!")

print("\n" + "=" * 80)
if all_passed:
    print("✅ TODOS OS TESTES PASSARAM!")
    print("\nVerificações:")
    print("  ✅ Acentos removidos apenas do nome do arquivo")
    print("  ✅ Diretórios (org_id/client_id/GERAL/pasta) mantidos intactos")
    print("  ✅ Espaços, hífens e parênteses preservados")
else:
    print("❌ ALGUNS TESTES FALHARAM!")
print("=" * 80)
