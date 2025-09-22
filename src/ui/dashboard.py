"""
Dashboard Streamlit para visualizar dados financeiros
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import sys
import os

# Adicionar path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Configuração da página
st.set_page_config(
    page_title="Gestor Financeiro",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configurações da API
API_URL = "http://localhost:8000"

def check_api_connection():
    """Verifica se a API está rodando"""
    try:
        response = requests.get(f"{API_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False

def get_dashboard_data(user_id: str):
    """Busca dados do dashboard"""
    try:
        response = requests.get(f"{API_URL}/dashboard/{user_id}")
        response.raise_for_status()
        return response.json()
    except:
        return None

def get_transactions(user_id: str):
    """Busca transações do usuário"""
    try:
        response = requests.get(f"{API_URL}/transactions/{user_id}")
        response.raise_for_status()
        return response.json()
    except:
        return None

def get_user_stats(user_id: str, period: str = "month"):
    """Busca estatísticas do usuário"""
    try:
        response = requests.get(f"{API_URL}/stats/{user_id}?period={period}")
        response.raise_for_status()
        return response.json()
    except:
        return None

def send_test_message(message: str, user_id: str):
    """Envia mensagem de teste"""
    try:
        response = requests.post(f"{API_URL}/webhook/message", json={
            "message": message,
            "user_id": user_id
        })
        response.raise_for_status()
        return response.json()
    except:
        return None

def main():
    st.title("💰 Gestor Financeiro via Chat")
    st.markdown("Dashboard para acompanhar gastos e receitas processados via mensagens")
    
    # Verificar conexão com API
    if not check_api_connection():
        st.error("🔴 API não está rodando! Execute primeiro: `uvicorn app:app`")
        st.stop()
    
    st.success("🟢 API conectada com sucesso!")
    
    # Sidebar
    st.sidebar.title("Configurações")
    user_id = st.sidebar.text_input("ID do Usuário", value="default_user")
    
    # Seção de teste de mensagens
    st.sidebar.markdown("---")
    st.sidebar.subheader("💬 Testar Mensagem")
    test_message = st.sidebar.text_input("Digite uma transação:")
    if st.sidebar.button("Enviar Mensagem"):
        if test_message:
            with st.spinner("Processando mensagem..."):
                result = send_test_message(test_message, user_id)
                if result and result.get("success"):
                    st.sidebar.success("✅ Mensagem processada!")
                    if result.get("alerts"):
                        for alert in result["alerts"]:
                            st.sidebar.warning(alert)
                    st.experimental_rerun()
                else:
                    st.sidebar.error("❌ Erro ao processar mensagem")
    
    # Dados principais
    dashboard_data = get_dashboard_data(user_id)
    if not dashboard_data:
        st.error("Erro ao carregar dados do dashboard")
        return
    
    # Métricas principais
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Saldo Total", f"R$ {dashboard_data['total_balance']:.2f}")
    
    with col2:
        total_expenses = sum(dashboard_data['monthly_expenses'].values())
        st.metric("💸 Gastos do Mês", f"R$ {total_expenses:.2f}")
    
    with col3:
        st.metric("📊 Transações", len(dashboard_data['recent_transactions']))
    
    with col4:
        alerts_count = len(dashboard_data.get('alerts', []))
        st.metric("⚠️ Alertas Ativos", alerts_count)
    
    # Alertas
    if dashboard_data.get('alerts'):
        st.markdown("### 🚨 Alertas Ativos")
        for alert in dashboard_data['alerts']:
            if "CRÍTICO" in alert:
                st.error(alert)
            else:
                st.warning(alert)
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    # Gráfico de gastos por categoria
    with col1:
        st.markdown("### 📊 Gastos por Categoria")
        if dashboard_data['monthly_expenses']:
            df_expenses = pd.DataFrame([
                {"Categoria": k, "Valor": v} 
                for k, v in dashboard_data['monthly_expenses'].items()
            ])
            
            fig = px.pie(
                df_expenses, 
                values='Valor', 
                names='Categoria',
                title="Distribuição de Gastos"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum gasto registrado ainda")
    
    # Gráfico de barras
    with col2:
        st.markdown("### 📈 Gastos vs Limites")
        if dashboard_data['monthly_expenses']:
            # Limites padrão (seria melhor buscar da API)
            default_limits = {
                'Comida': 800, 'Transporte': 400, 'Lazer': 300,
                'Saúde': 500, 'Mercado': 600, 'Moradia': 2000,
                'Educação': 400, 'Outros': 500
            }
            
            categories = list(dashboard_data['monthly_expenses'].keys())
            expenses = list(dashboard_data['monthly_expenses'].values())
            limits = [default_limits.get(cat, 500) for cat in categories]
            
            fig = go.Figure(data=[
                go.Bar(name='Gasto Atual', x=categories, y=expenses),
                go.Bar(name='Limite', x=categories, y=limits, opacity=0.6)
            ])
            
            fig.update_layout(barmode='group', title="Gastos vs Limites por Categoria")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nenhum dado para comparação")
    
    # Estatísticas detalhadas
    st.markdown("### 📈 Estatísticas Detalhadas")
    period = st.selectbox("Período", ["month", "week", "day"])
    
    stats = get_user_stats(user_id, period)
    if stats:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total de Transações", stats['total_transactions'])
            st.metric("Receitas", f"R$ {stats['total_revenue']:.2f}")
        
        with col2:
            st.metric("Gastos", f"R$ {stats['total_expenses']:.2f}")
            st.metric("Média por Transação", f"R$ {stats.get('average_transaction', 0):.2f}")
        
        with col3:
            balance = stats['total_revenue'] - stats['total_expenses']
            st.metric("Saldo do Período", f"R$ {balance:.2f}")
    
    # Tabela de transações recentes
    st.markdown("### 📋 Transações Recentes")
    transactions = get_transactions(user_id)
    if transactions and transactions.get('transactions'):
        df = pd.DataFrame(transactions['transactions'])
        
        # Formatar DataFrame
        df['amount'] = df['amount'].apply(lambda x: f"R$ {x:.2f}" if x else "N/A")
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%d/%m/%Y') if 'date' in df.columns else "N/A"
        
        # Mostrar colunas relevantes
        display_df = df[['raw_message', 'type', 'amount', 'category', 'place', 'date']].copy()
        display_df.columns = ['Mensagem', 'Tipo', 'Valor', 'Categoria', 'Local', 'Data']
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("Nenhuma transação encontrada")
    
    # Exemplos de mensagens
    st.sidebar.markdown("---")
    st.sidebar.subheader("💡 Exemplos de Mensagens")
    examples = [
        "Gastei R$ 25 no almoço",
        "Paguei R$ 40 de uber",
        "Recebi R$ 3500 de salário",
        "R$ 120 no supermercado",
        "Netflix R$ 29,90",
        "Conta de luz R$ 180"
    ]
    
    for example in examples:
        if st.sidebar.button(f"📝 {example}", key=f"ex_{example}"):
            result = send_test_message(example, user_id)
            if result and result.get("success"):
                st.sidebar.success("✅ Enviado!")
                st.experimental_rerun()

if __name__ == "__main__":
    main()
