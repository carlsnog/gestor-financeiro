"""
Serviço de alertas para monitorar limites de gastos e disparar notificações
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.database import SessionLocal, Transaction, Alert, AlertHistory
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class AlertService:
    """Serviço para gerenciar alertas financeiros"""
    
    def __init__(self):
        self.default_alerts = self._get_default_alert_config()
    
    def _get_default_alert_config(self) -> Dict[str, Any]:
        """Configuração padrão de alertas"""
        return {
            'category_limits': {
                'Comida': 800.0,
                'Transporte': 400.0,
                'Lazer': 300.0,
                'Saúde': 500.0,
                'Mercado': 600.0,
                'Moradia': 2000.0,
                'Educação': 400.0,
                'Outros': 500.0
            },
            'total_monthly_limit': 5000.0,
            'warning_threshold': 0.8,  # 80% do limite
            'critical_threshold': 0.95,  # 95% do limite
            'unusual_transaction_threshold': 1000.0,  # Valores acima disso geram alerta
        }
    
    def configure_user_alerts(self, user_id: str, alert_config: Dict[str, Any]):
        """Configura alertas personalizados para um usuário"""
        db = SessionLocal()
        try:
            # Remover alertas antigos do usuário
            db.query(Alert).filter(Alert.user_id == user_id).delete()
            
            # Adicionar novos alertas
            if 'category_limits' in alert_config:
                for category, limit in alert_config['category_limits'].items():
                    alert = Alert(
                        user_id=user_id,
                        alert_type='category_limit',
                        category=category,
                        limit_amount=limit,
                        period='month'
                    )
                    db.add(alert)
            
            if 'total_monthly_limit' in alert_config:
                alert = Alert(
                    user_id=user_id,
                    alert_type='total_balance',
                    limit_amount=alert_config['total_monthly_limit'],
                    period='month'
                )
                db.add(alert)
            
            db.commit()
            logger.info(f"Alertas configurados para usuário {user_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao configurar alertas: {e}")
            raise e
        finally:
            db.close()
    
    def check_alerts(self, user_id: str, transaction_data: Dict[str, Any]) -> List[str]:
        """Verifica alertas imediatos após uma transação"""
        alerts = []
        
        # Verificar transação incomum (valor alto)
        if transaction_data.get('amount', 0) > self.default_alerts['unusual_transaction_threshold']:
            alerts.append(
                f"⚠️ Transação de valor alto detectada: R$ {transaction_data['amount']:.2f}"
            )
        
        # Verificar apenas gastos para alertas de limite
        if transaction_data.get('type') != 'gasto':
            return alerts
        
        # Verificar limites por categoria
        category = transaction_data.get('category')
        if category and category in self.default_alerts['category_limits']:
            monthly_spent = self._get_monthly_spent_by_category(user_id, category)
            category_limit = self._get_category_limit(user_id, category)
            
            if monthly_spent >= category_limit * self.default_alerts['critical_threshold']:
                alerts.append(
                    f"🚨 CRÍTICO: Limite de {category} quase esgotado! "
                    f"R$ {monthly_spent:.2f} / R$ {category_limit:.2f}"
                )
            elif monthly_spent >= category_limit * self.default_alerts['warning_threshold']:
                alerts.append(
                    f"⚠️ AVISO: {int((monthly_spent/category_limit)*100)}% do limite de {category} utilizado. "
                    f"R$ {monthly_spent:.2f} / R$ {category_limit:.2f}"
                )
        
        # Verificar limite total mensal
        total_monthly_spent = self._get_total_monthly_spent(user_id)
        total_limit = self._get_total_limit(user_id)
        
        if total_monthly_spent >= total_limit * self.default_alerts['critical_threshold']:
            alerts.append(
                f"🚨 CRÍTICO: Orçamento mensal quase esgotado! "
                f"R$ {total_monthly_spent:.2f} / R$ {total_limit:.2f}"
            )
        elif total_monthly_spent >= total_limit * self.default_alerts['warning_threshold']:
            alerts.append(
                f"⚠️ AVISO: {int((total_monthly_spent/total_limit)*100)}% do orçamento mensal utilizado. "
                f"R$ {total_monthly_spent:.2f} / R$ {total_limit:.2f}"
            )
        
        return alerts
    
    def process_transaction_alerts(self, user_id: str, transaction_data: Dict[str, Any]) -> List[str]:
        """Processa alertas para uma transação e salva no histórico"""
        alerts = self.check_alerts(user_id, transaction_data)
        
        # Salvar alertas no histórico
        if alerts:
            self._save_alert_history(user_id, alerts, transaction_data)
        
        return alerts
    
    def get_active_alerts(self, user_id: str) -> List[str]:
        """Retorna alertas ativos para o usuário"""
        alerts = []
        
        # Verificar todos os limites atuais
        for category, limit in self.default_alerts['category_limits'].items():
            monthly_spent = self._get_monthly_spent_by_category(user_id, category)
            
            if monthly_spent >= limit * self.default_alerts['warning_threshold']:
                percentage = int((monthly_spent/limit)*100)
                if percentage >= 95:
                    alerts.append(f"🚨 {category}: {percentage}% do limite (R$ {monthly_spent:.2f}/{limit:.2f})")
                else:
                    alerts.append(f"⚠️ {category}: {percentage}% do limite (R$ {monthly_spent:.2f}/{limit:.2f})")
        
        # Verificar limite total
        total_monthly_spent = self._get_total_monthly_spent(user_id)
        total_limit = self._get_total_limit(user_id)
        
        if total_monthly_spent >= total_limit * self.default_alerts['warning_threshold']:
            percentage = int((total_monthly_spent/total_limit)*100)
            if percentage >= 95:
                alerts.append(f"🚨 Orçamento total: {percentage}% utilizado (R$ {total_monthly_spent:.2f}/{total_limit:.2f})")
            else:
                alerts.append(f"⚠️ Orçamento total: {percentage}% utilizado (R$ {total_monthly_spent:.2f}/{total_limit:.2f})")
        
        return alerts
    
    def _get_monthly_spent_by_category(self, user_id: str, category: str) -> float:
        """Calcula total gasto no mês por categoria"""
        db = SessionLocal()
        try:
            now = datetime.now()
            start_of_month = datetime(now.year, now.month, 1)
            
            result = db.query(Transaction)\
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.category == category,
                    Transaction.transaction_type == 'gasto',
                    Transaction.transaction_date >= start_of_month,
                    Transaction.is_active == True
                )\
                .all()
            
            return sum(t.amount for t in result if t.amount)
        finally:
            db.close()
    
    def _get_total_monthly_spent(self, user_id: str) -> float:
        """Calcula total gasto no mês"""
        db = SessionLocal()
        try:
            now = datetime.now()
            start_of_month = datetime(now.year, now.month, 1)
            
            result = db.query(Transaction)\
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_type == 'gasto',
                    Transaction.transaction_date >= start_of_month,
                    Transaction.is_active == True
                )\
                .all()
            
            return sum(t.amount for t in result if t.amount)
        finally:
            db.close()
    
    def _get_category_limit(self, user_id: str, category: str) -> float:
        """Busca limite configurado para categoria ou usa padrão"""
        db = SessionLocal()
        try:
            alert = db.query(Alert)\
                .filter(
                    Alert.user_id == user_id,
                    Alert.alert_type == 'category_limit',
                    Alert.category == category,
                    Alert.is_active == True
                )\
                .first()
            
            if alert and alert.limit_amount:
                return alert.limit_amount
            
            return self.default_alerts['category_limits'].get(category, 500.0)
        finally:
            db.close()
    
    def _get_total_limit(self, user_id: str) -> float:
        """Busca limite total configurado ou usa padrão"""
        db = SessionLocal()
        try:
            alert = db.query(Alert)\
                .filter(
                    Alert.user_id == user_id,
                    Alert.alert_type == 'total_balance',
                    Alert.is_active == True
                )\
                .first()
            
            if alert and alert.limit_amount:
                return alert.limit_amount
            
            return self.default_alerts['total_monthly_limit']
        finally:
            db.close()
    
    def _save_alert_history(self, user_id: str, alerts: List[str], transaction_data: Dict[str, Any]):
        """Salva alertas no histórico"""
        db = SessionLocal()
        try:
            for alert_message in alerts:
                alert_history = AlertHistory(
                    user_id=user_id,
                    message=alert_message,
                    alert_type='transaction_alert',
                    trigger_amount=transaction_data.get('amount'),
                    trigger_category=transaction_data.get('category')
                )
                db.add(alert_history)
            
            db.commit()
            logger.info(f"Alertas salvos no histórico para usuário {user_id}")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar histórico de alertas: {e}")
        finally:
            db.close()
    
    def get_alert_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retorna histórico de alertas"""
        db = SessionLocal()
        try:
            alerts = db.query(AlertHistory)\
                .filter(AlertHistory.user_id == user_id)\
                .order_by(AlertHistory.triggered_at.desc())\
                .limit(limit)\
                .all()
            
            return [
                {
                    'id': alert.id,
                    'message': alert.message,
                    'alert_type': alert.alert_type,
                    'triggered_at': alert.triggered_at.isoformat(),
                    'trigger_amount': alert.trigger_amount,
                    'trigger_category': alert.trigger_category
                }
                for alert in alerts
            ]
        finally:
            db.close()
    
    def generate_weekly_summary(self, user_id: str) -> Dict[str, Any]:
        """Gera resumo semanal para o usuário"""
        db = SessionLocal()
        try:
            # Última semana
            now = datetime.now()
            week_start = now - timedelta(weeks=1)
            
            weekly_transactions = db.query(Transaction)\
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date >= week_start,
                    Transaction.is_active == True
                )\
                .all()
            
            summary = {
                'period': f"{week_start.strftime('%d/%m')} - {now.strftime('%d/%m/%Y')}",
                'total_transactions': len(weekly_transactions),
                'total_spent': 0.0,
                'total_received': 0.0,
                'by_category': defaultdict(float),
                'top_expenses': [],
                'alerts_triggered': len(self.get_active_alerts(user_id))
            }
            
            for transaction in weekly_transactions:
                if transaction.amount:
                    if transaction.transaction_type == 'gasto':
                        summary['total_spent'] += transaction.amount
                        if transaction.category:
                            summary['by_category'][transaction.category] += transaction.amount
                    elif transaction.transaction_type == 'receita':
                        summary['total_received'] += transaction.amount
            
            # Top 5 gastos
            expenses = [t for t in weekly_transactions 
                       if t.transaction_type == 'gasto' and t.amount]
            summary['top_expenses'] = sorted(
                [{'amount': t.amount, 'category': t.category, 'details': t.details}
                 for t in expenses],
                key=lambda x: x['amount'],
                reverse=True
            )[:5]
            
            summary['by_category'] = dict(summary['by_category'])
            return summary
            
        finally:
            db.close()
