# Mapa de Cobertura - RC Gestor v1.2.64 STABLE
**Branch:** qa/fixpack-04  
**Data:** 24 de novembro de 2025  
**Gerado a partir de:** `.coverage` (pytest --cov)

---

## 📊 Resumo Geral

| Métrica | Valor |
|---------|-------|
| **Cobertura Total** | **40.4%** |
| **Total de Arquivos** | 287 |
| **Statements Totais** | 15,914 |
| **Statements Não Cobertos** | 9,172 |
| **Branches Totais** | 3,498 |
| **Branches Parciais** | 309 |

### Distribuição por Faixa de Cobertura

| Faixa | Quantidade | Percentual |
|-------|------------|------------|
| 🔴 **< 20%** | 104 arquivos | 36.2% |
| 🟡 **20-40%** | 26 arquivos | 9.1% |
| 🟢 **40-60%** | 18 arquivos | 6.3% |
| ✅ **60-100%** | 139 arquivos | 48.4% |

---

## 🎯 Top 30 Arquivos com Menor Cobertura

Arquivos críticos que estão arrastando a cobertura para baixo:

| # | Arquivo | Stmts | Miss | Cover | Categoria |
|---|---------|-------|------|-------|-----------|
| 1 | `src\modules\pdf_preview\views\main_window.py` | 609 | 536 | **9.4%** | PDF Preview |
| 2 | `src\modules\clientes\views\main_screen.py` | 573 | 504 | **9.8%** | Clientes |
| 3 | `src\modules\main_window\views\main_window.py` | 526 | 432 | **15.2%** | Main Window |
| 4 | `src\modules\hub\views\hub_screen.py` | 471 | 392 | **14.0%** | Hub |
| 5 | `src\modules\auditoria\views\main_frame.py` | 334 | 282 | **12.5%** | Auditoria |
| 6 | `src\modules\lixeira\views\lixeira.py` | 291 | 272 | **5.5%** | Lixeira |
| 7 | `src\modules\clientes\forms\client_form.py` | 244 | 228 | **5.3%** | Clientes |
| 8 | `src\modules\uploads\uploader_supabase.py` | 204 | 172 | **13.0%** | Uploads |
| 9 | `src\modules\main_window\app_actions.py` | 216 | 203 | **5.1%** | Main Window |
| 10 | `src\ui\dialogs\storage_uploader.py` | 213 | 192 | **7.7%** | UI/Dialogs |
| 11 | `src\modules\hub\controller.py` | 210 | 189 | **8.1%** | Hub |
| 12 | `src\core\db_manager\db_manager.py` | 201 | 42 | **75.7%** | Core ✅ |
| 13 | `src\app_core.py` | 199 | 171 | **11.4%** | App Core |
| 14 | `src\modules\auditoria\archives.py` | 198 | 22 | **85.3%** | Auditoria ✅ |
| 15 | `data\supabase_repo.py` | 197 | 158 | **16.2%** | Data Layer |
| 16 | `src\modules\auditoria\views\upload_flow.py` | 195 | 160 | **14.8%** | Auditoria |
| 17 | `src\modules\auditoria\service.py` | 192 | 31 | **85.5%** | Auditoria ✅ |
| 18 | `src\modules\auditoria\viewmodel.py` | 188 | 135 | **22.7%** | Auditoria |
| 19 | `src\utils\file_utils\bytes_utils.py` | 178 | 20 | **87.5%** | Utils ✅ |
| 20 | `src\modules\clientes\forms\client_picker.py` | 172 | 148 | **11.8%** | Clientes |
| 21 | `src\modules\clientes\forms\_upload.py` | 160 | 70 | **55.9%** | Clientes |
| 22 | `src\core\services\notes_service.py` | 158 | 63 | **59.5%** | Core |
| 23 | `src\infra\supabase\storage_client.py` | 152 | 52 | **60.2%** | Infra ✅ |
| 24 | `src\core\auth_bootstrap.py` | 153 | 59 | **59.3%** | Core |
| 25 | `src\modules\auditoria\views\dialogs.py` | 151 | 133 | **9.8%** | Auditoria |
| 26 | `src\infra\supabase\db_client.py` | 148 | 76 | **39.7%** | Infra |
| 27 | `src\core\auth\auth.py` | 137 | 2 | **97.7%** | Core ✅ |
| 28 | `src\core\services\lixeira_service.py` | 137 | 22 | **81.7%** | Core ✅ |
| 29 | `src\modules\main_window\controller.py` | 133 | 113 | **12.7%** | Main Window |
| 30 | `src\utils\text_utils.py` | 131 | 23 | **77.5%** | Utils ✅ |

---

## 🚨 Arquivos Grandes com Cobertura Crítica

**Critério:** Stmts >= 100 E Cover < 60%

Estes são os módulos **mais impactantes** para melhorar a cobertura global:

| Arquivo | Stmts | Miss | Cover | Impacto |
|---------|-------|------|-------|---------|
| **src\modules\pdf_preview\views\main_window.py** | 609 | 536 | 9.4% | 🔥🔥🔥 CRÍTICO |
| **src\modules\clientes\views\main_screen.py** | 573 | 504 | 9.8% | 🔥🔥🔥 CRÍTICO |
| **src\modules\main_window\views\main_window.py** | 526 | 432 | 15.2% | 🔥🔥🔥 CRÍTICO |
| **src\modules\hub\views\hub_screen.py** | 471 | 392 | 14.0% | 🔥🔥🔥 CRÍTICO |
| **src\modules\auditoria\views\main_frame.py** | 334 | 282 | 12.5% | 🔥🔥 ALTO |
| **src\modules\lixeira\views\lixeira.py** | 291 | 272 | 5.5% | 🔥🔥 ALTO |
| **src\modules\clientes\forms\client_form.py** | 244 | 228 | 5.3% | 🔥🔥 ALTO |
| **src\modules\uploads\uploader_supabase.py** | 204 | 172 | 13.0% | 🔥 MÉDIO |
| **src\modules\main_window\app_actions.py** | 216 | 203 | 5.1% | 🔥 MÉDIO |
| **src\ui\dialogs\storage_uploader.py** | 213 | 192 | 7.7% | 🔥 MÉDIO |
| **src\modules\hub\controller.py** | 210 | 189 | 8.1% | 🔥 MÉDIO |
| **src\app_core.py** | 199 | 171 | 11.4% | 🔥 MÉDIO |
| **data\supabase_repo.py** | 197 | 158 | 16.2% | 🔥 MÉDIO |
| **src\modules\auditoria\views\upload_flow.py** | 195 | 160 | 14.8% | 🔥 MÉDIO |
| **src\modules\auditoria\viewmodel.py** | 188 | 135 | 22.7% | 🟡 MODERADO |
| **src\modules\clientes\forms\client_picker.py** | 172 | 148 | 11.8% | 🟡 MODERADO |
| **src\modules\clientes\forms\_upload.py** | 160 | 70 | 55.9% | 🟡 MODERADO |
| **src\core\services\notes_service.py** | 158 | 63 | 59.5% | 🟡 MODERADO |
| **src\core\auth_bootstrap.py** | 153 | 59 | 59.3% | 🟡 MODERADO |
| **src\modules\auditoria\views\dialogs.py** | 151 | 133 | 9.8% | 🟡 MODERADO |
| **src\infra\supabase\db_client.py** | 148 | 76 | 39.7% | 🟡 MODERADO |
| **src\modules\main_window\controller.py** | 133 | 113 | 12.7% | 🟡 MODERADO |
| **src\ui\login\login.py** | 127 | 112 | 10.3% | 🟡 MODERADO |
| **src\ui\login_dialog.py** | 132 | 112 | 13.5% | 🟡 MODERADO |
| **src\core\services\clientes_service.py** | 129 | 25 | 78.1% | ✅ BOM |
| **src\ui\widgets\autocomplete_entry.py** | 128 | 128 | 0.0% | 🔥 MÉDIO |
| **src\modules\clientes\forms\client_subfolders_dialog.py** | 126 | 118 | 5.5% | 🟡 MODERADO |
| **src\ui\components\misc.py** | 126 | 93 | 21.4% | 🟡 MODERADO |
| **src\modules\clientes\views\pick_mode.py** | 120 | 97 | 15.1% | 🟡 MODERADO |
| **src\modules\hub\actions.py** | 119 | 108 | 8.0% | 🟡 MODERADO |
| **src\features\cashflow\repository.py** | 118 | 29 | 78.6% | ✅ BOM |
| **src\ui\dialogs\pdf_converter_dialogs.py** | 114 | 97 | 13.9% | 🟡 MODERADO |
| **src\ui\custom_dialogs.py** | 112 | 100 | 10.5% | 🟡 MODERADO |
| **src\modules\hub\authors.py** | 112 | 102 | 6.3% | 🟡 MODERADO |
| **src\app_status.py** | 117 | 0 | 97.9% | ✅ EXCELENTE |
| **src\utils\prefs.py** | 225 | 41 | 80.3% | ✅ BOM |
| **src\utils\themes.py** | 108 | 88 | 15.4% | 🟡 MODERADO |
| **src\modules\auditoria\views\layout.py** | 106 | 99 | 5.3% | 🟡 MODERADO |
| **src\modules\uploads\validation.py** | 102 | 60 | 32.8% | 🟡 MODERADO |

---

## 📁 Resumo por Área/Pasta

Análise agrupada por estrutura de pastas:

| Área | Arquivos | Stmts Totais | Cobertura Média | Status |
|------|----------|--------------|-----------------|--------|
| **infra/** | 22 | 860 | **53.6%** | 🟡 Moderado |
| **data/** | 3 | 260 | **47.5%** | 🟡 Moderado |
| **security/** | 1 | 35 | **95.1%** | ✅ Excelente |
| **src/core/** | 35 | 1,629 | **66.8%** | 🟢 Bom |
| **src/modules/clientes/** | 24 | 2,528 | **31.2%** | 🔴 Crítico |
| **src/modules/main_window/** | 7 | 937 | **28.4%** | 🔴 Crítico |
| **src/modules/pdf_preview/** | 9 | 987 | **21.8%** | 🔴 Crítico |
| **src/modules/hub/** | 11 | 931 | **22.5%** | 🔴 Crítico |
| **src/modules/uploads/** | 10 | 740 | **53.2%** | 🟡 Moderado |
| **src/modules/auditoria/** | 19 | 1,850 | **31.4%** | 🔴 Crítico |
| **src/modules/lixeira/** | 6 | 313 | **26.9%** | 🔴 Crítico |
| **src/ui/** | 68 | 2,547 | **12.3%** | 🔴🔴 MUITO CRÍTICO |
| **src/utils/** | 25 | 1,308 | **58.7%** | 🟡 Moderado |
| **src/helpers/** | 5 | 127 | **89.8%** | ✅ Excelente |
| **src/config/** | 4 | 59 | **85.0%** | ✅ Excelente |
| **adapters/** | 4 | 161 | **77.6%** | ✅ Bom |

### Análise Crítica por Área

#### 🔴🔴 EMERGÊNCIA (< 20% cobertura média)
- **src/ui/**: 12.3% - Camada de interface gráfica quase sem testes

#### 🔴 CRÍTICO (20-40% cobertura)
- **src/modules/pdf_preview/**: 21.8% - Visualizador de PDFs
- **src/modules/hub/**: 22.5% - Hub de funcionalidades
- **src/modules/lixeira/**: 26.9% - Lixeira
- **src/modules/main_window/**: 28.4% - Janela principal
- **src/modules/clientes/**: 31.2% - Módulo de clientes (GRANDE)
- **src/modules/auditoria/**: 31.4% - Auditoria

#### 🟡 MODERADO (40-60% cobertura)
- **data/**: 47.5% - Camada de dados
- **src/infra/**: 53.6% - Infraestrutura
- **src/modules/uploads/**: 53.2% - Upload de arquivos
- **src/utils/**: 58.7% - Utilitários

#### ✅ BOM (> 60% cobertura)
- **src/core/**: 66.8% - Core do app (BOA COBERTURA!)
- **adapters/**: 77.6% - Adaptadores
- **src/config/**: 85.0% - Configuração
- **src/helpers/**: 89.8% - Helpers
- **security/**: 95.1% - Criptografia

---

## 🎯 Lista de Prioridades para Chegar em ~60%

Para elevar a cobertura de **40.4%** para **~60%**, atacar nesta ordem:

### 🚨 P1 - CRÍTICO (Arquivos Gigantes com < 20% cover)

**Impacto estimado:** +8-10% de cobertura global

1. **src/modules/pdf_preview/views/main_window.py** (609 Stmts, 9.4% cover)
   - Visualizador de PDFs - testar navegação, zoom, renderização

2. **src/modules/clientes/views/main_screen.py** (573 Stmts, 9.8% cover)
   - Tela principal de clientes - testar listagem, filtros, ações

3. **src/modules/main_window/views/main_window.py** (526 Stmts, 15.2% cover)
   - Janela principal - testar menu, navegação, layout

4. **src/modules/hub/views/hub_screen.py** (471 Stmts, 14.0% cover)
   - Hub - testar cards, navegação, ações

5. **src/modules/auditoria/views/main_frame.py** (334 Stmts, 12.5% cover)
   - Frame de auditoria - testar grid, filtros

6. **src/modules/uploads/uploader_supabase.py** (204 Stmts, 13.0% cover)
   - Uploader - testar upload, progresso, cancelamento

7. **src/app_core.py** (199 Stmts, 11.4% cover)
   - Core da aplicação - testar inicialização, ciclo de vida

8. **data/supabase_repo.py** (197 Stmts, 16.2% cover)
   - Repository do Supabase - testar CRUD, queries

### 🔥 P2 - ALTO (Arquivos Grandes com 20-40% cover)

**Impacto estimado:** +4-6% de cobertura global

9. **src/modules/auditoria/viewmodel.py** (188 Stmts, 22.7% cover)
10. **src/modules/clientes/service.py** (223 Stmts, 57.5% cover) - quase lá!
11. **src/modules/main_window/controller.py** (133 Stmts, 12.7% cover)
12. **src/ui/login/login.py** (127 Stmts, 10.3% cover)
13. **src/ui/login_dialog.py** (132 Stmts, 13.5% cover)
14. **src/modules/uploads/validation.py** (102 Stmts, 32.8% cover)

### 🟡 P3 - MODERADO (Arquivos Médios com < 40% cover)

**Impacto estimado:** +2-3% de cobertura global

15. **src/modules/clientes/forms/client_form.py** (244 Stmts, 5.3% cover)
16. **src/modules/clientes/forms/client_picker.py** (172 Stmts, 11.8% cover)
17. **src/modules/lixeira/views/lixeira.py** (291 Stmts, 5.5% cover)
18. **src/ui/dialogs/storage_uploader.py** (213 Stmts, 7.7% cover)
19. **src/modules/hub/controller.py** (210 Stmts, 8.1% cover)
20. **src/modules/hub/actions.py** (119 Stmts, 8.0% cover)

### ✅ P4 - POLIMENTO (Arquivos com 40-60% cover)

**Impacto estimado:** +1-2% de cobertura global

21. **src/infra/supabase/db_client.py** (148 Stmts, 39.7% cover)
22. **src/core/services/notes_service.py** (158 Stmts, 59.5% cover)
23. **src/core/auth_bootstrap.py** (153 Stmts, 59.3% cover)
24. **src/modules/clientes/forms/_upload.py** (160 Stmts, 55.9% cover)

---

## 📈 Estratégia Recomendada

### Fase 1: Fundação (40% → 50%)
**Foco:** P1 (itens 1-8)
- Criar testes básicos para os "gigantes"
- Cobertura de happy paths e casos principais
- **Meta:** 50% em 2-3 semanas

### Fase 2: Consolidação (50% → 60%)
**Foco:** P2 (itens 9-14)
- Ampliar cobertura dos módulos de negócio
- Testes de casos de borda
- **Meta:** 60% em 3-4 semanas

### Fase 3: Excelência (60% → 75%)
**Foco:** P3 + P4
- Completar cobertura de dialogs e forms
- Testes de integração
- **Meta:** 75% em 4-6 semanas

---

## 💡 Insights e Observações

### Pontos Fortes ✅
- **src/core/**: 66.8% - Core bem testado!
- **security/crypto.py**: 95.1% - Criptografia coberta
- **src/helpers/**: 89.8% - Helpers bem testados
- **src/app_status.py**: 97.9% - Status monitor excelente
- **src/core/auth/auth.py**: 97.7% - Autenticação coberta

### Pontos Fracos 🔴
- **src/ui/**: 12.3% - Camada UI quase sem testes (GUI testada manualmente?)
- **Módulos gigantes**: PDF Preview, Clientes, Main Window com < 20%
- **Forms**: Formulários complexos com 5-15% de cobertura
- **Dialogs**: Diálogos com 0-10% de cobertura

### Recomendações Técnicas

1. **UI Testing Strategy**
   - Considerar testes de integração com `pytest-tkinter` ou similar
   - Separar lógica de apresentação (testar ViewModels/Controllers)
   - Mockar Tkinter onde possível

2. **Forms & Dialogs**
   - Criar fixtures reutilizáveis para setup de formulários
   - Testar validações e fluxos de dados separadamente

3. **Grandes Módulos**
   - Quebrar em submódulos testáveis
   - Aplicar padrão Repository/Service mais rigidamente
   - Aumentar cobertura de forma incremental (10% por sprint)

4. **Data Layer**
   - `data/supabase_repo.py` com 16.2% - priorizar testes de CRUD
   - Mockar Supabase client para testes rápidos

---

## 🔍 Arquivos com 100% de Cobertura

Total: **87 arquivos** com cobertura perfeita (30.3% do projeto)

Destaque para:
- `src/app_utils.py` (62 Stmts, 100%)
- `src/core/storage_key.py` (44 Stmts, 100%)
- `src/helpers/auth_utils.py` (31 Stmts, 100%)
- `src/modules/pdf_tools/pdf_batch_from_images.py` (78 Stmts, 100%)
- `infra/supabase/storage_helpers.py` (16 Stmts, 100%)

---

**Gerado automaticamente a partir de `python -m coverage report`**  
**Próxima atualização:** Após sprint de testes P1
