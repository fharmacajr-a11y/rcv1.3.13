# Configuração de Policies do Supabase Storage

## Bucket: rc-docs

Para garantir que usuários autenticados possam criar prefixos e fazer upload de arquivos no bucket `rc-docs`, configure as seguintes políticas no Supabase Dashboard:

### 1. Acessar Policies do Storage

1. Acesse o Supabase Dashboard
2. Vá em **Storage** > **Policies**
3. Selecione o bucket **rc-docs**

### 2. Políticas Necessárias

#### INSERT Policy (Upload de arquivos)
```sql
-- Nome: authenticated_users_insert
-- Role: authenticated
-- Operation: INSERT

CREATE POLICY authenticated_users_insert ON storage.objects
FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'rc-docs');
```

#### SELECT Policy (Listagem/Download de arquivos)
```sql
-- Nome: authenticated_users_select
-- Role: authenticated
-- Operation: SELECT

CREATE POLICY authenticated_users_select ON storage.objects
FOR SELECT
TO authenticated
USING (bucket_id = 'rc-docs');
```

#### UPDATE Policy (Atualização de arquivos)
```sql
-- Nome: authenticated_users_update
-- Role: authenticated
-- Operation: UPDATE

CREATE POLICY authenticated_users_update ON storage.objects
FOR UPDATE
TO authenticated
USING (bucket_id = 'rc-docs')
WITH CHECK (bucket_id = 'rc-docs');
```

#### DELETE Policy (Remoção de arquivos)
```sql
-- Nome: authenticated_users_delete
-- Role: authenticated
-- Operation: DELETE

CREATE POLICY authenticated_users_delete ON storage.objects
FOR DELETE
TO authenticated
USING (bucket_id = 'rc-docs');
```

### 3. Policy Restrita por Organização (OPCIONAL)

Se desejar restringir acesso apenas aos arquivos da organização do usuário, você pode adicionar condições baseadas no prefixo:

```sql
-- Exemplo: Restrição por prefixo da ORG
-- Assumindo que o prefixo começa com org_id

CREATE POLICY org_restricted_select ON storage.objects
FOR SELECT
TO authenticated
USING (
  bucket_id = 'rc-docs' AND
  (
    -- Permitir se o usuário pertence à organização do prefixo
    EXISTS (
      SELECT 1 FROM public.memberships
      WHERE user_id = auth.uid()
      AND position(org_id::text IN name) > 0
    )
  )
);
```

**Nota:** Esta policy mais complexa requer ajustes dependendo da estrutura da sua tabela `memberships` e do formato dos prefixos.

### 4. Testar as Policies

Após configurar as policies, teste-as:

1. Faça login na aplicação
2. Tente criar um novo cliente com "Salvar + Enviar para Supabase"
3. Verifique nos logs se o placeholder `.keep` foi criado
4. Verifique no Storage se o prefixo aparece corretamente

#### Teste via SQL Explorer

```sql
-- Verificar se o usuário pode inserir
SELECT storage.can_insert_object('rc-docs', 'test-org/12345678901234-test-000001/.keep', auth.uid());

-- Listar objetos (deve retornar os objetos se a policy SELECT está correta)
SELECT * FROM storage.objects WHERE bucket_id = 'rc-docs' LIMIT 10;
```

### 5. Troubleshooting

#### Erro: Row-level security policy violation
- Verifique se as policies estão habilitadas para o role `authenticated`
- Verifique se o bucket `rc-docs` existe
- Confirme que o usuário está autenticado (`auth.uid()` retorna um valor)

#### Erro: Invalid key
- Verifique se o caminho não contém caracteres especiais inválidos
- O prefixo deve seguir o formato: `{org_id}/{cnpj}-{slug}-{client_id:06d}`

#### Placeholder não aparece no Storage
- Verifique os logs da aplicação para ver se houve erro
- Confirme que o usuário tem permissão INSERT
- Teste manualmente via SQL Explorer

### 6. Verificação de Permissões

Execute no SQL Editor:

```sql
-- Ver policies do bucket rc-docs
SELECT * FROM storage.policies WHERE bucket_id = 'rc-docs';

-- Testar se usuário autenticado pode acessar
SELECT auth.uid(); -- Deve retornar o ID do usuário logado
```

## Referências

- [Supabase Storage Policies Documentation](https://supabase.com/docs/guides/storage/security/access-control)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)
