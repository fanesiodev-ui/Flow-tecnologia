# ContaFácil — Gerador Inteligente de Relatórios Contábeis

Sistema SaaS que transforma balancetes (Excel ou PDF) em relatórios profissionais em PDF, com linguagem simples e visual premium, prontos para enviar ao cliente.

---

## 🚀 Como Rodar (Início Rápido)

```bash
# 1. Clone ou navegue até a pasta do projeto
cd Flow-tecnologia

# 2. Execute o script de inicialização
chmod +x run.sh
./run.sh
```

O script instala tudo automaticamente e abre o sistema no navegador.

**Acessos:**
- 🌐 **Frontend:** http://localhost:8000/app
- 📖 **API Docs:** http://localhost:8000/docs

---

## 📦 Estrutura do Projeto

```
Flow-tecnologia/
│
├── backend/                    # API FastAPI (Python)
│   ├── main.py                 # Rotas da API
│   ├── config.py               # Configurações
│   ├── requirements.txt        # Dependências Python
│   │
│   ├── models/
│   │   └── schemas.py          # Modelos de dados (Pydantic)
│   │
│   ├── processors/
│   │   ├── excel_processor.py  # Lê e classifica balancetes Excel
│   │   ├── pdf_processor.py    # Lê e classifica balancetes PDF
│   │   └── data_analyzer.py    # Gera insights e recomendações
│   │
│   ├── generators/
│   │   └── report_generator.py # Gera o PDF profissional (ReportLab)
│   │
│   └── storage/
│       ├── uploads/            # Arquivos temporários
│       └── reports/            # PDFs gerados
│
├── frontend/
│   ├── index.html              # Interface SaaS (Tailwind CSS)
│   └── app.js                  # Lógica do frontend
│
├── samples/
│   ├── criar_balancete.py      # Cria um Excel de exemplo
│   └── balancete_exemplo.xlsx  # Gerado pelo script acima
│
├── run.sh                      # Script de início rápido
└── .env.example                # Variáveis de ambiente
```

---

## ⚙️ Instalação Manual (sem o run.sh)

```bash
# 1. Crie e ative o ambiente virtual
python3 -m venv backend/.venv
source backend/.venv/bin/activate      # Linux/Mac
# backend\.venv\Scripts\activate       # Windows

# 2. Instale as dependências
pip install -r backend/requirements.txt

# 3. Gere um balancete de exemplo
python3 samples/criar_balancete.py

# 4. Inicie o servidor
cd backend
uvicorn main:app --reload
```

---

## 🎯 Funcionalidades

### Upload e Processamento
- Aceita arquivos **Excel (.xlsx, .xls)** e **PDF**
- Extração automática de: Faturamento, Impostos, Custos e Despesas
- Fallback para dados demo se o arquivo não puder ser lido

### Relatório PDF Gerado
- **Capa** com nome da empresa e período
- **Cards** de indicadores: Faturamento, Impostos, Lucro Líquido
- **Tabela** completa de composição das despesas
- **Análise inteligente** em linguagem simples (sem termos técnicos)
- **Recomendações estratégicas** baseadas nos números

### White Label
- Cor principal e secundária personalizáveis
- Nome do escritório contábil no rodapé
- Nome do contador responsável

### Análise Inteligente
O sistema classifica automaticamente a saúde financeira:

| Indicador | Saudável | Atenção | Crítico |
|---|---|---|---|
| Margem de Lucro | ≥ 20% | 10–20% | < 10% |
| Carga Tributária | ≤ 15% | 15–25% | > 25% |
| Custos Operacionais | ≤ 40% | 40–60% | > 60% |

---

## 📡 API Endpoints

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/generate-report` | Upload de balancete → gera PDF |
| `POST` | `/api/demo-report` | Gera PDF com dados fictícios |
| `GET`  | `/api/download/{id}` | Download do PDF gerado |
| `GET`  | `/health` | Status da API |
| `GET`  | `/docs` | Documentação interativa (Swagger) |

### Exemplo com curl

```bash
# Gerar relatório de demonstração
curl -X POST http://localhost:8000/api/demo-report \
  -F "empresa_nome=Padaria São João LTDA" \
  -F "periodo=Março/2024" \
  -F "company_name=Contabilidade Silva" \
  -F "accountant_name=João Silva CRC-SP 12345" \
  -F "primary_color=#1E40AF"

# Resposta:
# {"success": true, "report_id": "...", "download_url": "/api/download/..."}

# Baixar o PDF
curl -o relatorio.pdf http://localhost:8000/api/download/{report_id}
```

---

## 🛠️ Tecnologias

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.9+ · FastAPI |
| Geração PDF | ReportLab 4.x |
| Leitura Excel | Pandas + openpyxl |
| Leitura PDF | pdfplumber |
| Frontend | HTML + Tailwind CSS (via CDN) |
| Validação | Pydantic v2 |

---

## 🔮 Próximos Passos (Roadmap)

- [ ] Autenticação de usuários (cada contador tem seu login)
- [ ] Histórico de relatórios por cliente
- [ ] Upload de logo do escritório no PDF
- [ ] Envio por e-mail direto do sistema
- [ ] Comparativo com mês anterior
- [ ] Integração com sistemas contábeis (Domínio, Questor, etc.)
- [ ] Planos e cobrança (Stripe)
- [ ] Banco de dados para persistência (PostgreSQL)

---

## ❓ Problemas Comuns

**O frontend não conecta à API:**
> Verifique se o backend está rodando: `cd backend && uvicorn main:app --reload`

**Erro ao ler o Excel:**
> O sistema tenta identificar automaticamente as colunas. Se não conseguir, usa dados demo. Certifique-se que o balancete tem colunas de "Descrição" e "Saldo/Valor".

**PDF não abre:**
> Certifique-se que o `report_id` está correto e que o arquivo ainda existe em `backend/storage/reports/`.

---

Desenvolvido com foco em **simplicidade**, **valor para o cliente** e **escalabilidade futura**.
