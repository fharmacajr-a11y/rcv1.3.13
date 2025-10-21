# PR9 - Pipeline salvar_e_upload_docs etapas reais

## Arquivos criados/alterados
- ui/forms/pipeline.py
- ui/forms/actions.py

## Etapas do pipeline
- validate_inputs: verifica conectividade (get_supabase_state), exibe warnings e logs existentes, valida campos/duplicatas e prepara UploadCtx com valores.
- prepare_payload: chama salvar_cliente, resolve org/bucket, mantém log "Bucket em uso: %s", pergunta subpasta, coleta arquivos e prepara contexto.
- perform_uploads: cria BusyDialog, espelha arquivos locais, realiza upload (com exec_postgrest), preservando logs "Upload OK" e erros Falha ao copiar local/Subpasta criada etc.
- finalize_state: fecha dialogo, mostra mensagem de sucesso/erro, destrói janela auxiliar e chama self.carregar() (executado após o worker via fter).

## Logs preservados
- "Tentativa de envio bloqueada...", "Bucket em uso: %s", "Falha ao copiar local: %s", "Upload OK: %s" e demais mensagens originais foram mantidos.

## Compatibilidade
- Assinatura e retorno de salvar_e_upload_docs inalterados.
- _salvar_e_upload_docs_impl agora delega ao contexto (retorna imediatamente quando abortado).
