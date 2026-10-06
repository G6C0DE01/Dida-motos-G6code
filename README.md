# Dida Motos — Sistema de Gestão de Estoque

Projeto Integrador II (FATEC Taquaritinga) — sistema de gestão de estoque
para a oficina Dida Motos (Monte Alto - SP), desenvolvido em **Django +
MySQL**, conforme o escopo do projeto.

## Estrutura dos apps

- **pecas** — cadastro de peças, categorias, fabricantes, localização física, modelos de moto compatíveis (módulo A do escopo).
- **movimentacoes** — entradas, saídas e ajustes de estoque, com histórico completo por usuário (módulo B).
- **ordens_servico** — clientes, motocicletas e ordens de reparo/serviço, com itens de peças usadas (módulo C).
- **fornecedores** — cadastro de fornecedores e histórico de compras/cotações (módulo D).
- **relatorios** — estoque por categoria, peças em falta, peças paradas, custo total, rotatividade e previsão de falta (módulo E).
- **core** — dashboard inicial (equivalente à tela do protótipo).

## Setup local (Windows)

### 1. Criar e ativar o ambiente virtual

Abra o terminal do VS Code **na pasta do projeto** e rode:

```
python -m venv venv
venv\Scripts\activate
```

### 2. Instalar as dependências

```
pip install -r requirements.txt
```

### 3. Configurar o banco de dados

Copie `.env.example` para `.env` (mesma pasta do `manage.py`) e ajuste os
dados de acesso ao seu MySQL local:

```
copy .env.example .env
```

Edite o `.env` e preencha `DB_USER`, `DB_PASSWORD`, etc. Se preferir testar
rapidamente sem MySQL instalado, troque `DB_ENGINE=mysql` por
`DB_ENGINE=sqlite` no `.env`.

Crie o banco no MySQL (uma vez só), pelo MySQL Workbench ou linha de comando:

```sql
CREATE DATABASE dida_motos CHARACTER SET utf8mb4;
```

### 4. Rodar as migrations

```
python manage.py migrate
```

Isso já cria todas as tabelas **e popula as 8 categorias padrão do escopo**
(Motor, Transmissão, Suspensão, Freios, Pneus, Acessórios, Eletrônicos,
Consumíveis) automaticamente.

### 5. Criar um usuário administrador

```
python manage.py createsuperuser
```

Esse é o primeiro usuário do sistema (superusuário) — ele já entra sem
precisar de ninguém pra aprovar, e é quem vai cadastrar os demais
funcionários pela tela própria do sistema (veja "Cadastro de
funcionários" abaixo). Também acessa o `/admin/`.

### 6. Rodar o servidor

```
python manage.py runserver
```

Acesse:
- `http://127.0.0.1:8000/entrar/` — Login
- `http://127.0.0.1:8000/` — Dashboard (exige login)
- `http://127.0.0.1:8000/admin/` — Administração (apoio/backup)
- `http://127.0.0.1:8000/funcionarios/` — Cadastro de funcionários (só gerentes)
- `http://127.0.0.1:8000/relatorios/estoque-por-categoria/` — Relatórios

## Login e cadastro de funcionários

O sistema exige login (usuário + senha) para qualquer tela, exceto a
própria tela de login e a de recuperação de senha. **Não existe
autocadastro público** — só um usuário do grupo "Gerentes" (ou
superusuário) pode criar acesso pra outra pessoa.

- **Login**: `/entrar/`
- **Cadastrar um funcionário**: um gerente entra em **Funcionários** no
  menu (`/funcionarios/novo/`) e preenche só o nome completo e a função
  (Gerente ou Mecânico) — sem e-mail, sem escolher usuário ou senha. O
  sistema gera o nome de usuário a partir do nome (ex.: "Guilherme Silva"
  → `guilherme.s`) e uma senha temporária, mostrada uma única vez na tela
  para ser repassada ao funcionário.
- **Primeiro login**: com usuário e senha temporária, o sistema força a
  troca de senha antes de liberar qualquer outra tela.
- **Revogar/reativar acesso**: também em `/funcionarios/`, com um botão
  por linha — substitui a necessidade de mexer no `/admin/` no dia a dia.
- Uma conta desativada tenta logar normalmente, mas vê a mensagem "Sua
  conta está desativada. Fale com um administrador para reativar o
  acesso."

## Segurança em produção

Em desenvolvimento (`DEBUG=True` no `.env`) nada muda. Quando o sistema for
publicado de verdade (`DEBUG=False`), o `config/settings.py` liga
automaticamente um conjunto de proteções recomendadas pelo próprio Django:

- Redirecionamento forçado para HTTPS (`SECURE_SSL_REDIRECT`).
- Cookies de sessão e CSRF marcados como `Secure` (só trafegam em HTTPS) e
  o cookie de sessão como `HttpOnly` (não acessível via JavaScript).
- HSTS (`SECURE_HSTS_SECONDS` e afins), instruindo o navegador a sempre
  usar HTTPS nesse domínio.
- `X-Content-Type-Options: nosniff` e `X-Frame-Options: DENY`.

**Importante:** essas opções só funcionam se o servidor de produção já
estiver atrás de HTTPS (com certificado válido). Ativar `DEBUG=False` sem
HTTPS configurado faz o site parar de responder a `http://` (por causa do
redirecionamento). Os valores podem ser ajustados via variáveis de
ambiente — veja os comentários em `.env.example`.

## Testes automatizados

O projeto tem uma suíte de testes (Django `TestCase`) cobrindo login,
cadastro de funcionário pelo gerente (geração de usuário/senha, troca de
senha obrigatória), estoque (entrada/saída/ajuste e suas validações),
Ordens de Serviço (geração de número, desconto automático de estoque dos
itens, edição/remoção), cadastro de cliente+veículo (validação de CPF,
busca de cliente existente), fornecedores, paginação das listas e
exportação CSV dos relatórios. Para rodar tudo:

```
python manage.py test
```

(usa o mesmo banco configurado no `.env`; para rodar sem MySQL instalado,
defina `DB_ENGINE=sqlite` antes do comando, como no setup local acima.)

## Estado atual do projeto

O que já está pronto: modelos de dados completos; telas próprias (fora do
admin) para Peças, Movimentações, Ordens de Serviço (com Clientes e
Motocicletas), Fornecedores e as 6 telas de relatório do módulo E, no
visual do protótipo, com paginação e exportação CSV; dashboard inicial
com gráfico de entradas x saídas; e cadastro de funcionário pelo gerente
(sem autocadastro público), com senha temporária e troca obrigatória no
primeiro login. Ao salvar uma Ordem de Serviço, o estoque das peças
usadas é descontado automaticamente (fica registrado em Movimentações).

O cadastro de cliente prioriza o veículo: a tela de "Novo veículo" pede
primeiro os dados da moto e, em seguida, resolve o cliente — reaproveita
um já cadastrado (por busca ou por CPF batendo) ou cria um novo só com
nome/CPF/telefone. O CPF é validado localmente pelo dígito verificador
(sem depender de nenhuma API externa — a Receita Federal não oferece uma
gratuita para isso).

O painel `/admin/` continua disponível como apoio/backup para um
superusuário, mas o uso do dia a dia (incluindo cadastro de funcionários)
é feito pelas telas próprias do sistema, acessíveis pelo menu lateral.
