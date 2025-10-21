# PR2 - Pipeline salvar_e_upload_docs

## Arquivos tocados
- ui/forms/actions.py
- ui/forms/pipeline.py

## Tamanho de salvar_e_upload_docs
- Antes: 308 linhas
- Depois: 308 linhas (implementação renomeada para `_salvar_e_upload_docs_impl`; wrapper mantém assinatura original)

## Assinatura e retorno
- Assinatura preservada: `salvar_e_upload_docs(self, row, ents: dict, arquivos_selecionados: list | None, win=None)`
- Retorno inalterado: repassa o resultado da implementação original

## Extrações não realizadas
- Nenhum bloco foi extraído; o método possui lógica interdependente (fluxo de validação/upload/cleanup com efeitos em UI e Supabase) e qualquer refatoração adicional exigiria testes integrados para garantir compatibilidade.
