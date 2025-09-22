# 📱 Configuração WhatsApp (Twilio)

**Guia completo para configurar a integração WhatsApp com Twilio**

---

## 🎯 **Visão Geral**

Este guia configura a integração entre o Gestor Financeiro e WhatsApp usando a API da Twilio, permitindo:
- ✅ Receber mensagens de transações
- ✅ Processar automaticamente via NLP
- ✅ Responder com confirmações
- ✅ Enviar alertas e comandos

---

## 🔑 **1. Criar Conta Twilio**

### **Cadastro Grátis**
1. Acesse: [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Cadastre-se (email + telefone)
3. Verifique seu número de telefone
4. Acesse o **Console Dashboard**

### **Créditos Grátis**
- 🎁 **$15 USD** grátis para teste
- Suficiente para **~1000 mensagens**
- Sem cobrança inicial

---

## ⚙️ **2. Configurar WhatsApp Sandbox**

### **Ativar Sandbox**
1. No Console Twilio: **Develop** → **Messaging** → **Try it out** → **Send a WhatsApp message**
2. **URL**: [https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
3. Copie o **código de ativação** (ex: `join abc123`)

### **Conectar Seu WhatsApp**
1. **Adicione** o número Twilio nos seus contatos: `+1 (415) 523-8886`
2. **Envie** via WhatsApp: `join abc123` (substitua pelo seu código)
3. **Aguarde** confirmação: *"You are now connected to the sandbox"*

✅ **Sandbox configurado!** Agora você pode enviar/receber mensagens.

---

## 🛠️ **3. Obter Credenciais**

### **Localizar Credenciais**
1. **Console Twilio** → **Account Dashboard**
2. **Account Info** (lado direito):
   - **Account SID**: `ACxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: Clique em "Show" → `xxxxxxxxxxxxxxxxxx`

### **Configurar no Projeto**
```bash
# Editar arquivo .env
vim .env

# Adicionar credenciais:
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

---

## 🌐 **4. Expor Webhook Publicamente**

### **Instalar ngrok**
```bash
# macOS (Homebrew)
brew install ngrok

# Ubuntu/Debian
sudo snap install ngrok

# Ou baixar: https://ngrok.com/download
```

### **Expor API Local**
```bash
# Terminal 1: Iniciar API
./start-api

# Terminal 2: Expor publicamente
ngrok http 8000
```

### **Copiar URL HTTPS**
```
Session Status    online
Forwarding        https://abc123.ngrok.io -> http://localhost:8000
```
📝 **Anote** a URL HTTPS: `https://abc123.ngrok.io`

---

## 🔗 **5. Configurar Webhook no Twilio**

### **Cadastrar Webhook URL**
1. **Console Twilio** → **WhatsApp Sandbox Settings**
2. **URL**: [https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
3. **Campo "When a message comes in"**:
   - URL: `https://abc123.ngrok.io/whatsapp/webhook`
   - Method: `POST`
4. **Salvar configurações**

✅ **Webhook configurado!** Mensagens agora chegam na sua API.

---

## 🧪 **6. Testar Integração**

### **Teste Básico**
1. **WhatsApp** → Envie para `+1 (415) 523-8886`:
   ```
   gastei 25 reais no almoço
   ```
2. **Aguarde resposta**:
   ```
   GASTO REGISTRADO
   Valor: R$ 25.00
   Categoria: Comida
   Data: hoje
   
   Transacao salva com sucesso!
   ```

### **Comandos Disponíveis**
```
💰 Transações:
• "gastei 50 reais no uber"
• "recebi 1000 reais de salario"  
• "mercado 120 reais ontem"

🎯 Comandos:
• "saldo" → Resumo financeiro
• "ajuda" → Lista de comandos
```

### **Teste Automatizado**
```bash
# Executar suite de testes
python scripts/test_whatsapp.py
```

---

## 🚨 **7. Solução de Problemas**

### **❌ "Não recebo mensagens"**

**Verificar:**
1. **Sandbox ativo**: Código `join` enviado corretamente
2. **Webhook URL**: URL ngrok correta no Twilio Console
3. **API rodando**: `curl http://localhost:8000/health`
4. **Ngrok funcionando**: `curl https://abc123.ngrok.io/health`

**Debug:**
```bash
# Ver logs da API
./start-api

# Ver requests ngrok
http://localhost:4040
```

### **❌ "Webhook não funciona"**

**Verificações:**
```bash
# Testar webhook diretamente
curl -X POST http://localhost:8000/whatsapp/webhook \
  -d "Body=teste" \
  -d "From=whatsapp:+5511999999999"

# Verificar resposta
# Status 200 + XML = ✅ Funcionando
```

### **❌ "Credenciais inválidas"**

**Verificar `.env`:**
```bash
# Testar credenciais
python -c "
import os
from twilio.rest import Client
client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
print('✅ Credenciais válidas:', client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch().status)
"
```

### **❌ "Número não autorizado"**
- **Sandbox**: Apenas números pré-autorizados
- **Solução**: Adicionar número ou upgrade para conta paga

---

## 💰 **8. Produção (Opcional)**

### **Upgrade para Conta Paga**
- **Vantagens**: Qualquer número, sem sandbox
- **Custo**: ~$0.005 por mensagem
- **Setup**: Verificar número business no Twilio

### **Webhook HTTPS**
- **Deploy**: Heroku, Digital Ocean, AWS
- **SSL**: Certificado obrigatório para produção  
- **URL**: `https://seudominio.com/whatsapp/webhook`

---

## 📋 **9. Checklist Final**

### **✅ Pré-requisitos**
- [ ] Conta Twilio criada
- [ ] Sandbox WhatsApp configurado  
- [ ] Número conectado via `join`
- [ ] Credenciais no `.env`

### **✅ Configuração Local**
- [ ] API rodando: `./start-api`
- [ ] Ngrok expondo: `ngrok http 8000`  
- [ ] Webhook URL configurada no Twilio
- [ ] Teste básico funcionando

### **✅ Comandos Funcionando**
- [ ] Registrar gasto: `"gastei 20 reais"`
- [ ] Registrar receita: `"recebi 100 reais"`
- [ ] Ver saldo: `"saldo"`
- [ ] Ver ajuda: `"ajuda"`

---

## 🎉 **Resultado Final**

Agora você pode:
- 📱 **Registrar transações** via WhatsApp naturalmente
- 🤖 **Receber confirmações** automáticas
- 📊 **Ver saldo** a qualquer momento  
- 🚨 **Receber alertas** de gastos por categoria
- 💡 **Usar comandos** para consultas rápidas

**🚀 Seu gestor financeiro pessoal via WhatsApp está funcionando!**

---

## 🆘 **Suporte**

- **📖 Documentação**: [README.md](../README.md)
- **🧪 Testes**: `python scripts/test_whatsapp.py`
- **🐛 Issues**: GitHub Issues
- **📞 Twilio**: [Help Center](https://help.twilio.com)

---

**✨ Configure uma vez, use para sempre! 🎯**