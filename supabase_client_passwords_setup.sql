-- ============================================================================
-- TABELA: client_passwords
-- Descrição: Armazenamento de senhas criptografadas de clientes
-- Segurança: RLS habilitado (apenas owner da organização)
-- ============================================================================

-- 1. Criar tabela
CREATE TABLE IF NOT EXISTS client_passwords (
    id BIGSERIAL PRIMARY KEY,
    org_id TEXT NOT NULL,
    client_name TEXT NOT NULL,
    service TEXT NOT NULL,
    username TEXT,
    password_enc TEXT,
    notes TEXT,
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_client_passwords_org_id 
    ON client_passwords(org_id);

CREATE INDEX IF NOT EXISTS idx_client_passwords_updated_at 
    ON client_passwords(updated_at DESC);

-- 3. Adicionar comentários
COMMENT ON TABLE client_passwords IS 'Senhas criptografadas de clientes (ORG-aware, owner-only)';
COMMENT ON COLUMN client_passwords.org_id IS 'ID da organização (FK para organizations)';
COMMENT ON COLUMN client_passwords.client_name IS 'Nome/razão social do cliente';
COMMENT ON COLUMN client_passwords.service IS 'Nome do serviço/sistema';
COMMENT ON COLUMN client_passwords.username IS 'Nome de usuário/login';
COMMENT ON COLUMN client_passwords.password_enc IS 'Senha criptografada (Fernet)';
COMMENT ON COLUMN client_passwords.notes IS 'Observações adicionais';
COMMENT ON COLUMN client_passwords.created_by IS 'ID do usuário que criou';
COMMENT ON COLUMN client_passwords.created_at IS 'Data/hora de criação';
COMMENT ON COLUMN client_passwords.updated_at IS 'Data/hora da última atualização';

-- 4. Habilitar RLS (Row Level Security)
ALTER TABLE client_passwords ENABLE ROW LEVEL SECURITY;

-- 5. Criar política de acesso: apenas owner da organização
CREATE POLICY "owner_full_access" ON client_passwords
    FOR ALL
    USING (
        org_id IN (
            SELECT org_id 
            FROM memberships
            WHERE user_id = auth.uid()
            AND role = 'owner'
        )
    );

-- 6. Opcional: Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_client_passwords_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_client_passwords_updated_at
    BEFORE UPDATE ON client_passwords
    FOR EACH ROW
    EXECUTE FUNCTION update_client_passwords_updated_at();

-- ============================================================================
-- VERIFICAÇÃO E TESTES
-- ============================================================================

-- Verificar tabela criada
SELECT 
    table_name, 
    table_type 
FROM information_schema.tables 
WHERE table_name = 'client_passwords';

-- Verificar colunas
SELECT 
    column_name, 
    data_type, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'client_passwords'
ORDER BY ordinal_position;

-- Verificar índices
SELECT 
    indexname, 
    indexdef 
FROM pg_indexes 
WHERE tablename = 'client_passwords';

-- Verificar RLS habilitado
SELECT 
    schemaname,
    tablename, 
    rowsecurity 
FROM pg_tables 
WHERE tablename = 'client_passwords';

-- Verificar políticas RLS
SELECT 
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename = 'client_passwords';

-- ============================================================================
-- EXEMPLO DE USO (após criar a tabela)
-- ============================================================================

-- Inserir registro de teste (substitua valores conforme necessário)
/*
INSERT INTO client_passwords (
    org_id,
    client_name,
    service,
    username,
    password_enc,
    notes,
    created_by
) VALUES (
    'org_123',
    'Cliente Exemplo LTDA',
    'Sistema Anvisa',
    'admin@cliente.com',
    'gAAAAABh...token_criptografado...==',
    'Acesso administrativo',
    'user_123'
);
*/

-- Consultar registros de uma organização (apenas owner verá)
/*
SELECT 
    id,
    client_name,
    service,
    username,
    '••••••' as password_masked,
    notes,
    created_by,
    created_at,
    updated_at
FROM client_passwords
WHERE org_id = 'org_123'
ORDER BY updated_at DESC;
*/

-- ============================================================================
-- LIMPEZA (use com cuidado em produção!)
-- ============================================================================

-- Remover trigger
-- DROP TRIGGER IF EXISTS trigger_update_client_passwords_updated_at ON client_passwords;
-- DROP FUNCTION IF EXISTS update_client_passwords_updated_at();

-- Remover políticas RLS
-- DROP POLICY IF EXISTS "owner_full_access" ON client_passwords;

-- Remover tabela (PERDA DE DADOS!)
-- DROP TABLE IF EXISTS client_passwords;
