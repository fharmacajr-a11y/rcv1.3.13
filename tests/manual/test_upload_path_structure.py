"""
Script de teste para validar a estrutura de caminhos de upload após Fase 8.
"""

from src.modules.uploads.validation import build_remote_path

# Simula upload de pasta "sifap" com arquivos
test_cases = [
    # (cnpj, relative_path, subfolder, client_id, org_id, expected)
    ("12345678000190", "arquivo.pdf", "sifap", 148, "ORG123", "ORG123/148/GERAL/sifap/arquivo.pdf"),
    ("12345678000190", "subpasta/arquivo.pdf", "sifap", 148, "ORG123", "ORG123/148/GERAL/sifap/subpasta/arquivo.pdf"),
    (
        "12345678000190",
        "Certidão de Regularidade.pdf",
        "sifap",
        148,
        "ORG123",
        "ORG123/148/GERAL/sifap/Certidão de Regularidade.pdf",
    ),
    (
        "12345678000190",
        "CONTRATO SOCIAL - ALTERAÇÃO.pdf",
        "sifap",
        148,
        "ORG123",
        "ORG123/148/GERAL/sifap/CONTRATO SOCIAL - ALTERAÇÃO.pdf",
    ),
]

print("=" * 80)
print("TESTE DE ESTRUTURA DE CAMINHOS - FASE 8")
print("=" * 80)

all_passed = True
for cnpj, relative, subfolder, client_id, org_id, expected in test_cases:
    result = build_remote_path(
        cnpj,
        relative,
        subfolder,
        client_id=client_id,
        org_id=org_id,
    )
    passed = result == expected
    all_passed = all_passed and passed

    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status}")
    print(f"  Input: relative_path={relative}, subfolder={subfolder}")
    print(f"  Expected: {expected}")
    print(f"  Got:      {result}")

print("\n" + "=" * 80)
if all_passed:
    print("✅ TODOS OS TESTES PASSARAM!")
else:
    print("❌ ALGUNS TESTES FALHARAM!")
print("=" * 80)
