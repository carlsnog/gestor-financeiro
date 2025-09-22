"""
Serviço para processamento e armazenamento de transações
Integra com o ExtratorFinanceiro e normaliza dados
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models.database import SessionLocal, Transaction, User
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class TransactionService:
    """Serviço para gerenciar transações financeiras"""
    
    def __init__(self):
        self.normalization_rules = self._load_normalization_rules()
    
    def _load_normalization_rules(self) -> Dict[str, Any]:
        """Carrega regras de normalização para categorias e lugares"""
        return {
            'category_synonyms': {
                'comida': ['alimentação', 'food', 'refeição'],
                'transporte': ['transport', 'locomoção', 'viagem'],
                'mercado': ['supermercado', 'grocery', 'compras'],
                'moradia': ['casa', 'home', 'residência', 'habitação'],
                'saúde': ['health', 'médico', 'hospital'],
                'educação': ['education', 'ensino', 'escola'],
                'lazer': ['entretenimento', 'diversão', 'fun']
            },
            'place_synonyms': {
                'extra': ['supermercado extra'],
                'pão de açúcar': ['pao de acucar', 'paodeacucar'],
                'netflix': ['netflix brasil'],
                'spotify': ['spotify premium'],
            },
            'amount_thresholds': {
                'small': 50.0,
                'medium': 200.0,
                'large': 500.0
            }
        }
    
    def normalize_extracted_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza e melhora os dados extraídos"""
        normalized = extracted_data.copy()
        
        # Normalizar categoria
        if extracted_data.get('category'):
            normalized['category'] = self._normalize_category(extracted_data['category'])
        
        # Normalizar lugar
        if extracted_data.get('place'):
            normalized['place'] = self._normalize_place(extracted_data['place'])
        
        # Normalizar data (se não tiver, usar hoje)
        if not normalized.get('date'):
            normalized['date'] = datetime.now().strftime('%Y-%m-%d')
        
        # Adicionar classificação de valor
        if normalized.get('amount'):
            normalized['amount_category'] = self._classify_amount(normalized['amount'])
        
        return normalized
    
    def _normalize_category(self, category: str) -> str:
        """Normaliza categoria usando sinônimos"""
        category_lower = category.lower()
        
        for standard_category, synonyms in self.normalization_rules['category_synonyms'].items():
            if category_lower in synonyms or category_lower == standard_category:
                return standard_category.capitalize()
        
        return category.capitalize()
    
    def _normalize_place(self, place: str) -> str:
        """Normaliza lugar usando sinônimos"""
        place_lower = place.lower()
        
        for standard_place, synonyms in self.normalization_rules['place_synonyms'].items():
            if place_lower in synonyms or place_lower == standard_place:
                return standard_place.title()
        
        return place.title()
    
    def _classify_amount(self, amount: float) -> str:
        """Classifica valor em categorias"""
        thresholds = self.normalization_rules['amount_thresholds']
        
        if amount <= thresholds['small']:
            return 'small'
        elif amount <= thresholds['medium']:
            return 'medium'
        elif amount <= thresholds['large']:
            return 'large'
        else:
            return 'very_large'
    
    def save_transaction(self, user_id: str, raw_message: str, extracted_data: Dict[str, Any], timestamp: datetime) -> int:
        """Salva transação no banco de dados"""
        db = SessionLocal()
        try:
            # Normalizar dados extraídos
            normalized_data = self.normalize_extracted_data(extracted_data)
            
            # Criar objeto Transaction
            transaction = Transaction(
                user_id=user_id,
                raw_message=raw_message,
                transaction_type=normalized_data.get('type', 'desconhecido'),
                amount=normalized_data.get('amount'),
                currency=normalized_data.get('currency', 'BRL'),
                category=normalized_data.get('category'),
                place=normalized_data.get('place'),
                details=normalized_data.get('details'),
                transaction_date=self._parse_date(normalized_data.get('date')) or timestamp,
                confidence=normalized_data.get('meta', {}).get('confidence', 0.0),
                extraction_metadata=normalized_data.get('meta', {}),
                created_at=timestamp
            )
            
            db.add(transaction)
            db.commit()
            db.refresh(transaction)
            
            logger.info(f"Transação salva: ID {transaction.id}")
            return transaction.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Erro ao salvar transação: {e}")
            raise e
        finally:
            db.close()
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Converte string de data para datetime"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            logger.warning(f"Não foi possível parsear data: {date_str}")
            return None
    
    def get_user_transactions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Busca transações do usuário"""
        db = SessionLocal()
        try:
            transactions = db.query(Transaction)\
                .filter(Transaction.user_id == user_id, Transaction.is_active == True)\
                .order_by(Transaction.created_at.desc())\
                .limit(limit)\
                .all()
            
            return [self._transaction_to_dict(t) for t in transactions]
        finally:
            db.close()
    
    def get_dashboard_data(self, user_id: str) -> Dict[str, Any]:
        """Retorna dados para o dashboard"""
        db = SessionLocal()
        try:
            # Data de início do mês atual
            now = datetime.now()
            start_of_month = datetime(now.year, now.month, 1)
            
            # Buscar transações do mês
            monthly_transactions = db.query(Transaction)\
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date >= start_of_month,
                    Transaction.is_active == True
                )\
                .all()
            
            # Calcular saldo total
            total_balance = 0.0
            monthly_expenses = defaultdict(float)
            
            for transaction in monthly_transactions:
                if transaction.amount:
                    if transaction.transaction_type == 'receita':
                        total_balance += transaction.amount
                    elif transaction.transaction_type == 'gasto':
                        total_balance -= transaction.amount
                        if transaction.category:
                            monthly_expenses[transaction.category] += transaction.amount
            
            # Últimas transações
            recent_transactions = db.query(Transaction)\
                .filter(Transaction.user_id == user_id, Transaction.is_active == True)\
                .order_by(Transaction.created_at.desc())\
                .limit(10)\
                .all()
            
            return {
                'total_balance': round(total_balance, 2),
                'monthly_expenses': dict(monthly_expenses),
                'recent_transactions': [self._transaction_to_dict(t) for t in recent_transactions]
            }
        finally:
            db.close()
    
    def get_user_stats(self, user_id: str, period: str = "month") -> Dict[str, Any]:
        """Retorna estatísticas detalhadas do usuário"""
        db = SessionLocal()
        try:
            # Definir período
            now = datetime.now()
            if period == "month":
                start_date = datetime(now.year, now.month, 1)
            elif period == "week":
                start_date = now - timedelta(weeks=1)
            else:  # day
                start_date = now - timedelta(days=1)
            
            # Buscar transações do período
            transactions = db.query(Transaction)\
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.transaction_date >= start_date,
                    Transaction.is_active == True
                )\
                .all()
            
            # Calcular estatísticas
            stats = {
                'period': period,
                'total_transactions': len(transactions),
                'total_revenue': 0.0,
                'total_expenses': 0.0,
                'by_category': defaultdict(lambda: {'count': 0, 'total': 0.0}),
                'by_type': defaultdict(lambda: {'count': 0, 'total': 0.0}),
                'average_transaction': 0.0,
                'confidence_distribution': defaultdict(int)
            }
            
            for transaction in transactions:
                if transaction.amount:
                    # Por tipo
                    stats['by_type'][transaction.transaction_type]['count'] += 1
                    stats['by_type'][transaction.transaction_type]['total'] += transaction.amount
                    
                    # Receitas vs gastos
                    if transaction.transaction_type == 'receita':
                        stats['total_revenue'] += transaction.amount
                    elif transaction.transaction_type == 'gasto':
                        stats['total_expenses'] += transaction.amount
                    
                    # Por categoria
                    if transaction.category:
                        stats['by_category'][transaction.category]['count'] += 1
                        stats['by_category'][transaction.category]['total'] += transaction.amount
                
                # Distribuição de confiança
                if transaction.confidence:
                    confidence_bucket = int(transaction.confidence * 10) / 10
                    stats['confidence_distribution'][confidence_bucket] += 1
            
            # Calcular médias
            if stats['total_transactions'] > 0:
                stats['average_transaction'] = (stats['total_revenue'] + stats['total_expenses']) / stats['total_transactions']
            
            # Converter defaultdict para dict normal
            stats['by_category'] = dict(stats['by_category'])
            stats['by_type'] = dict(stats['by_type'])
            stats['confidence_distribution'] = dict(stats['confidence_distribution'])
            
            return stats
        finally:
            db.close()
    
    def _transaction_to_dict(self, transaction: Transaction) -> Dict[str, Any]:
        """Converte Transaction para dicionário"""
        return {
            'id': transaction.id,
            'raw_message': transaction.raw_message,
            'type': transaction.transaction_type,
            'amount': transaction.amount,
            'currency': transaction.currency,
            'category': transaction.category,
            'place': transaction.place,
            'details': transaction.details,
            'date': transaction.transaction_date.isoformat() if transaction.transaction_date else None,
            'confidence': transaction.confidence,
            'created_at': transaction.created_at.isoformat(),
            'is_verified': transaction.is_verified
        }
