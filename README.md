# 💰 Gestor Financeiro 

**Sistema inteligente de gestão financeira pessoal via WhatsApp**

Aplicação que permite registrar e acompanhar gastos e receitas através de mensagens de WhatsApp, com processamento inteligente de linguagem natural, alertas automáticos e dashboard interativo.

---

## 🎯 **Funcionalidades**

### ✅ **Core MVP (Implementado)**
- **📱 Integração WhatsApp**: Receba e processe transações via Twilio
- **🧠 Processamento NLP**: Extração automática de entidades (valor, categoria, data)
- **💾 Armazenamento**: Normalização e persistência em SQLite
- **⚡ Alertas**: Notificações automáticas por categoria e gastos
- **📊 Dashboard**: Interface web interativa com Streamlit
- **🔍 API REST**: Endpoints completos para integração

### 📱 **Comandos WhatsApp**
```
💬 Registrar transações:
• "Gastei R$ 25 no almoço"
• "Recebi R$ 1000 de salário"  
• "Uber 15 reais para casa"
• "Netflix R$ 29,90 mensal"

🎯 Comandos úteis:
• "saldo" → Ver resumo financeiro
• "ajuda" → Lista de comandos disponíveis
```

---

## 🛠️ **Stack Tecnológica**

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: Streamlit (Dashboard)
- **NLP**: Sistema híbrido (Regras + Spacy)
- **WhatsApp**: Twilio API (sandbox + produção)
- **Deploy**: Local + Docker (futuro)

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

### **2. Configurar WhatsApp (Opcional)**
```bash
# Edite suas credenciais Twilio
vim .env

# Teste a integração
python scripts/test_whatsapp.py
```

### **3. Inicializar Serviços**
```bash
# Terminal 1: API Backend
./start-api

# Terminal 2: Dashboard (opcional)  
./start-dashboard

# Terminal 3: Ngrok (para WhatsApp)
ngrok http 8000
```

---

## 📁 **Estrutura do Projeto**

```
gestor-financeiro/
├── 🚀 setup              # Setup completo
├── 🌐 start-api          # Iniciar API
├── 📊 start-dashboard    # Iniciar dashboard
├── 
├── src/                  # Código fonte
│   ├── api/             # FastAPI backend
│   │   └── app.py       # Aplicação principal
│   ├── core/            # Lógica de negócio
│   │   ├── models/      # Modelos de dados
│   │   ├── services/    # Serviços de negócio
│   │   └── registrador/ # NLP extractor
│   ├── integrations/    # Integrações externas
│   │   └── whatsapp_service.py
│   └── ui/              # Interface Streamlit
│       └── dashboard.py
├── 
├── config/              # Configurações
│   ├── requirements.txt # Dependências Python
│   └── .env.example     # Template configuração
├── 
├── scripts/             # Utilitários
│   ├── evaluator.py     # Avaliação do NLP
│   ├── message_simulator.py # Simulador
│   └── test_whatsapp.py # Testes WhatsApp
├── 
├── docs/                # Documentação
│   ├── WHATSAPP_SETUP.md
│   └── MIGRATION_NOTES.md
├── 
├── data/                # Dados
│   └── sample_data.jsonl
├── 
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

### **WhatsApp Integration**  
```http
POST   /whatsapp/webhook    # Webhook Twilio
POST   /whatsapp/send       # Enviar mensagem
```

**📚 Documentação completa**: `http://localhost:8000/docs`

---

## 📱 **Integração WhatsApp**

### **✅ Status: Implementado e Funcionando**

**Configuração:**
1. Credenciais Twilio no `.env`
2. Webhook URL no Twilio Console  
3. Número autorizado no Sandbox

**Funcionalidades:**
- ✅ Receber transações via mensagem
- ✅ Processar NLP e salvar no banco
- ✅ Responder com confirmação automática  
- ✅ Comandos: `saldo`, `ajuda`
- ✅ Alertas automáticos por categoria
- ✅ Suporte a emojis e formatação

**📖 Setup detalhado:** [docs/WHATSAPP_SETUP.md](docs/WHATSAPP_SETUP.md)

---

## 🧪 **Avaliação e Testes**

### **Executar Avaliações**
```bash
# Avaliar performance do NLP
python scripts/evaluator.py

# Simular transações
python scripts/message_simulator.py  

# Testar integração WhatsApp
python scripts/test_whatsapp.py
```

### **Métricas de Performance**
- **Precisão NLP**: ~85-90% 
- **Categorização**: 12+ categorias automáticas
- **Tempo resposta**: <500ms por transação
- **WhatsApp latência**: ~1-2 segundos

---

## 🎨 **Como Usar**

### **1. Via WhatsApp (Recomendado)**
- Conecte seu número no Twilio Sandbox
- Envie: `"gastei 25 reais no almoço"`
- Receba confirmação automática e alertas

### **2. Via Dashboard Web**
- Acesse: `http://localhost:8501`
- Visualize gastos, receitas e gráficos
- Gerencie alertas e categorias

### **3. Via API REST**
- Use endpoints REST para integrar
- Documentação: `http://localhost:8000/docs`

---

## 🔧 **Configuração Avançada**

### **Variáveis de Ambiente (.env)**
```bash
# Twilio WhatsApp
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Aplicação
DEBUG=True
LOG_LEVEL=INFO
DATABASE_URL=sqlite:///./financeiro.db
```

### **Deploy Produção**
- Configure webhook HTTPS no Twilio
- Use PostgreSQL em vez de SQLite
- Configure logs centralizados
- Implement autenticação/autorização

---

## 📈 **Roadmap**

### **🎯 Próximas Features**
- [ ] **Autenticação**: Login social + JWT
- [ ] **Multi-usuário**: Isolamento por usuário  
- [ ] **Categorias customizadas**: Usuário define
- [ ] **Relatórios**: PDF + Email automático
- [ ] **Integrações**: Bancos + Cartões + PIX

### **🚀 Melhorias Técnicas**
- [ ] **Docker**: Containerização completa
- [ ] **CI/CD**: Deploy automático
- [ ] **Monitoring**: Logs + Metrics + Alertas
- [ ] **Cache**: Redis para performance
- [ ] **Queue**: Background jobs para processar

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

---

## 🆘 **Suporte**

- **📖 Documentação**: [docs/](docs/)
- **🐛 Issues**: Use GitHub Issues
- **💬 Discussões**: GitHub Discussions  

---

**✨ Desenvolvido com ❤️ para facilitar o controle financeiro pessoal**