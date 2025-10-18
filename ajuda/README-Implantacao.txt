RC - Gestor de Clientes (Build Windows)

1) Executável:
   - Use o .exe gerado por: pyinstaller build/rc_gestor.spec

2) Credenciais:
   - Funcionário entra com e-mail e senha do Supabase (Auth).
   - URL e ANON KEY já embutidas no app (publishable key).
   - RLS no Supabase controla o acesso aos dados.

3) Requisitos:
   - Internet habilitada.

4) Segurança:
   - Nenhum .env no pacote. Nada de service_role.
   - Tokens ficam apenas em memória.

5) Suporte:
   - Em caso de erro de sessão, feche e abra o app para relogar.
