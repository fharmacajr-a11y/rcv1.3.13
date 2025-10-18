#!/bin/bash
# Script de finalização da release v1.0.29
# Substitua YOUR_GITHUB_TOKEN pelo seu token com scope 'repo'

TOKEN="YOUR_GITHUB_TOKEN"
REPO="fharmacajr-a11y/rcv1.3.13"
PR_NUMBER=1

echo "=================================================="
echo "RELEASE v1.0.29 - AUTOMATION SCRIPT"
echo "=================================================="
echo ""

# ========================================
# PASSO 1: Verificar status do PR #1
# ========================================
echo "[1/5] Verificando status do PR #1..."
curl -X GET \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/pulls/$PR_NUMBER" \
  | jq '{state, mergeable, mergeable_state, merged, title}'

echo ""
read -p "Pressione ENTER para continuar com o merge..."
echo ""

# ========================================
# PASSO 2: Fazer o merge do PR
# ========================================
echo "[2/5] Fazendo merge do PR #1 na main..."
MERGE_RESPONSE=$(curl -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/$REPO/pulls/$PR_NUMBER/merge" \
  -d '{
    "commit_title": "Integrate v1.0.29 into main history",
    "merge_method": "merge"
  }')

echo "$MERGE_RESPONSE" | jq '{merged, sha, message}'
MERGE_SHA=$(echo "$MERGE_RESPONSE" | jq -r '.sha')
echo ""
echo "✓ Merge SHA: $MERGE_SHA"
echo ""

# ========================================
# PASSO 3: Obter SHA da branch main
# ========================================
echo "[3/5] Obtendo SHA da branch main..."
MAIN_SHA=$(curl -s \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$REPO/git/ref/heads/main" \
  | jq -r '.object.sha')

echo "✓ Main SHA: $MAIN_SHA"
echo ""

# ========================================
# PASSO 4: Criar tag v1.0.29
# ========================================
echo "[4/5] Criando tag v1.0.29..."
TAG_RESPONSE=$(curl -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/$REPO/git/refs" \
  -d "{
    \"ref\": \"refs/tags/v1.0.29\",
    \"sha\": \"$MAIN_SHA\"
  }")

echo "$TAG_RESPONSE" | jq '{ref, object}'
echo ""

# ========================================
# PASSO 5: Criar Release
# ========================================
echo "[5/5] Criando Release v1.0.29..."
RELEASE_RESPONSE=$(curl -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  -H "Content-Type: application/json" \
  "https://api.github.com/repos/$REPO/releases" \
  -d '{
    "tag_name": "v1.0.29",
    "target_commitish": "main",
    "name": "v1.0.29",
    "body": "### v1.0.29 – Highlights\n\n- CI/Build\n  - Pipeline \"RC – test & build\" com Python 3.12 e pip-audit (report-only)\n  - Estrutura unificada de scripts/healthcheck\n  - Smoke + priorização de testes de PDF\n  - Retry de rede com `urllib3.Retry` e timeouts\n  - 24 testes estabilizados\n\n- Código & Features\n  - Dedup de utils/imports\n  - HubScreen adicionado à navegação\n  - Entrypoint unificado (app_core/gui)\n  - Filtros de logs e ajustes spec/env\n\n- Qualidade & Docs\n  - Pré-commit: remoção de BOM e reformatação (44 arquivos)\n  - `.gitattributes` normalizado (EOL)\n  - ZIP de referência via LFS\n  - Segurança: pip-audit rodando no CI\n\n> Observação: aviso benigno no job de testes — \"No files were found for .pytest_cache.\"",
    "draft": false,
    "prerelease": false
  }')

echo "$RELEASE_RESPONSE" | jq '{id, html_url, tag_name, name, published_at}'
RELEASE_URL=$(echo "$RELEASE_RESPONSE" | jq -r '.html_url')

echo ""
echo "=================================================="
echo "✓ RELEASE CONCLUÍDA"
echo "=================================================="
echo "Release URL: $RELEASE_URL"
echo ""
echo "Próximos passos:"
echo "1. Acesse o workflow para obter o asset ZIP"
echo "2. Calcule o SHA256 do ZIP"
echo "3. Atualize docs/CLAUDE-SONNET-v1.0.29/LOG.md"
echo "=================================================="
