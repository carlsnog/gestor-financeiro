# 💰 Gestor Financeiro 

**Sistema inteligente de gestão financeira pessoal**

Aplicação que permite registrar e acompanhar gastos e receitas através de mensagens de texto, com processamento inteligente de linguagem natural, alertas automáticos e dashboard interativo.

---

## 🎯 **Funcionalidades**

### ✅ **Core MVP (Implementado)**
- **🧠 Processamento NLP**: Extração automática de entidades (valor, categoria, data)
- **💾 Armazenamento**: Normalização e persistência em SQLite
- **⚡ Alertas**: Notificações automáticas por categoria e gastos
- **📊 Dashboard**: Interface web interativa com Streamlit
- **🔍 API REST**: Endpoints completos para integração

### 📱 **Exemplos de Transações**
```
💬 Registrar transações:
• "Gastei R$ 25 no almoço"
• "Recebi R$ 1000 de salário"  
• "Uber 15 reais para casa"
• "Netflix R$ 29,90 mensal"
```

---

## 🛠️ **Stack Tecnológica**

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: Streamlit (Dashboard)
- **NLP**: Sistema híbrido (Regras + Machine Learning)

---

## 🚀 **Início Rápido**

### **1. Setup Inicial**
```bash
# Clone o repositório
git clone <repo-url>
cd gestor-financeiro

# Configure tudo automaticamente
./setup
```

### **2. Inicializar Serviços**
```bash
# Terminal 1: API Backend
./start-api

# Terminal 2: Dashboard (opcional)  
./start-dashboard
```

---

## 📁 **Estrutura do Projeto**

```
gestor-financeiro/
├── setup              # Setup completo
├── start-api          # Iniciar API
├── start-dashboard    # Iniciar dashboard
├── src/                  # Código fonte
│   ├── api/             # FastAPI backend
│   │   └── app.py       # Aplicação principal
│   ├── core/            # Lógica de negócio
│   │   ├── models/      # Modelos de dados
│   │   ├── services/    # Serviços de negócio
│   │   └── registrador/ # NLP extractor
│   └── ui/              # Interface Streamlit
│       └── dashboard.py
├── config/              # Configurações
│   ├── requirements.txt # Dependências Python
│   └── .env.example     # Template configuração
├── scripts/             # Utilitários
│   ├── evaluator.py     # Avaliação do NLP
│   ├── message_simulator.py # Simulador
├── data/                # Dados
│   └── sample_data.jsonl
└── tests/               # Testes
    ├── avaliador.py
    └── tests_extrator.py
```

---

## 🌐 **API Endpoints**

### **Core Endpoints**
```http
GET    /transactions        # Listar transações
POST   /transactions        # Criar transação
GET    /dashboard/{user_id} # Dashboard data
GET    /alerts/{user_id}    # Alertas ativos
```

**📚 Documentação completa**: `http://localhost:8000/docs`

---

## 🧪 **Avaliação e Testes**

### **Executar Avaliações**
```bash
# Avaliar performance do NLP
python scripts/evaluator.py

# Simular transações
python scripts/message_simulator.py  

```

---

## 🎨 **Como Usar**

### **1. Via Dashboard Web**
- Acesse: `http://localhost:8501`
- Visualize gastos, receitas e gráficos
- Gerencie alertas e categorias

### **2. Via API REST**
- Use endpoints REST para integrar
- Documentação: `http://localhost:8000/docs`

---

## 🔧 **Configuração Avançada**

### **Variáveis de Ambiente (.env)**
```bash
# Aplicação
DEBUG=True
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./financeiro.db
```

---

## 🤝 **Contribuições**

1. Fork o repositório
2. Crie uma branch: `git checkout -b feature/nova-feature`
3. Commit: `git commit -am 'Adiciona nova feature'`
4. Push: `git push origin feature/nova-feature`
5. Abra um Pull Request

---

## 📄 **Licença**

Este projeto está sob licença MIT. Veja [LICENSE](LICENSE) para detalhes.