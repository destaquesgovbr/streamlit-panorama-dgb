# Streamlit Boilerplate - Plataforma DGB

Template repository para criar aplicações Streamlit na Plataforma DGB (Destaques do Governo Brasileiro).

## Sobre este Template

Este é um template pronto para uso que fornece a estrutura básica para desenvolver e deployar aplicações Streamlit na infraestrutura DGB no Google Cloud Platform.

## Desenvolvimento Local

### Pré-requisitos

- Python 3.11+
- pip

### Instalação

1. Clone este repositório (ou use "Use this template" no GitHub):
   ```bash
   git clone https://github.com/destaquesgovbr/streamlit-boilerplate.git
   cd streamlit-boilerplate
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Execute o app localmente:
   ```bash
   streamlit run app/main.py
   ```

4. Acesse `http://localhost:8501` no navegador

### Desenvolvimento

- Código da aplicação: `app/main.py`
- Componentes reutilizáveis: `app/components/`
- Funções auxiliares: `app/utils/`
- Configuração do Streamlit: `.streamlit/config.toml`
- Metadados do app: `.streamlit-app.yaml`

### Testes

```bash
# Instalar dependências de desenvolvimento
pip install -r requirements-dev.txt

# Rodar testes
pytest

# Rodar testes com cobertura
pytest --cov=app tests/
```

## Deploy na Plataforma DGB

### 1. Registrar o App

1. Abra um issue no repositório [infra](https://github.com/destaquesgovbr/infra/issues/new?template=register-streamlit-app.md)
2. Preencha os dados da aplicação:
   - Nome do app (slug, ex: `budget-analysis`)
   - Nome do repositório
   - Descrição
   - Resource tier (small/medium/large)
   - Tipo de service account (compartilhada/dedicada)

3. Aguarde a aprovação e merge do PR automático

### 2. Configurar Nome do App

Edite o arquivo `.github/workflows/build-deploy.yml` e altere a variável `APP_NAME` para o nome registrado no passo 1:

```yaml
env:
  APP_NAME: seu-app-name  # Altere aqui
```

### 3. Atualizar Metadados

Edite o arquivo `.streamlit-app.yaml` com as informações da sua aplicação:

```yaml
name: "Nome da Sua Aplicação"
description: "Descrição clara do que o app faz"
owner:
  name: "Seu Nome/Time"
  email: "seu-email@exemplo.com"
# ... outros campos
```

### 4. Deploy Automático

Faça push para a branch `main`:

```bash
git add .
git commit -m "Configure app for DGB platform"
git push origin main
```

O GitHub Actions irá automaticamente:
1. Construir a imagem Docker
2. Fazer push para o Artifact Registry
3. Fazer deploy no Cloud Run
4. Exibir a URL pública do app

### 5. Acesso a Secrets (Opcional)

Se seu app precisa acessar secrets do Secret Manager:

1. Abra um issue em [infra](https://github.com/destaquesgovbr/infra/issues/new?template=request-secret-access.md)
2. Especifique quais secrets seu app precisa acessar
3. Aguarde aprovação e apply do Terraform

Para usar secrets no código:

```python
from google.cloud import secretmanager

client = secretmanager.SecretManagerServiceClient()
secret_name = f"projects/inspire-7-finep/secrets/my-secret/versions/latest"
response = client.access_secret_version(request={"name": secret_name})
secret_value = response.payload.data.decode("UTF-8")
```

## Estrutura do Projeto

```
streamlit-boilerplate/
├── .github/
│   └── workflows/
│       └── build-deploy.yml    # CI/CD workflow
├── app/
│   ├── __init__.py
│   ├── main.py                 # Aplicação principal
│   ├── components/             # Componentes reutilizáveis
│   │   └── __init__.py
│   └── utils/                  # Funções auxiliares
│       └── __init__.py
├── tests/
│   ├── __init__.py
│   └── test_app.py             # Testes
├── .streamlit/
│   └── config.toml             # Configuração do Streamlit
├── .streamlit-app.yaml         # Metadados para catálogo
├── Dockerfile                  # Container definition
├── requirements.txt            # Dependências Python
├── requirements-dev.txt        # Dependências de desenvolvimento
├── .dockerignore
├── .gitignore
└── README.md
```

## Resource Tiers

Escolha o tier adequado para sua aplicação:

| Tier | CPU | Memória | Max Instâncias | Uso Recomendado |
|------|-----|---------|----------------|-----------------|
| small | 1 | 512MB | 3 | Apps leves, dashboards simples |
| medium | 1 | 1GB | 5 | Apps moderados, processamento leve |
| large | 2 | 2GB | 10 | Apps pesados, ML, processamento intenso |

## Documentação Adicional

- [Plataforma Streamlit DGB - Overview](https://github.com/destaquesgovbr/infra/blob/main/docs/streamlit-platform.md)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)

## Suporte

Para problemas ou dúvidas:
1. Consulte a [documentação da plataforma](https://github.com/destaquesgovbr/infra/blob/main/docs/streamlit-platform.md)
2. Abra um issue em [infra](https://github.com/destaquesgovbr/infra/issues)

## Licença

AGPL-3.0 License - veja [LICENSE](LICENSE) para detalhes.
