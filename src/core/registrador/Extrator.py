# Implementando o extrator rule-based
import re
from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any
import json

from registrador.gerenciador_modelo import CategoryModel

class ExtratorFinanceiro:
    """Extrator rule-based para transações financeiras em português"""
    
    def __init__(self):
        self.category_model = CategoryModel()
        # Mapa de keywords para categorias
        self.CATEGORIAS_MAP = {
            'comida': ['pastel', 'pizza', 'hamburguer', 'lanche', 'jantar', 'almoço', 'café', 'restaurante', 'lanchonete', 'padaria', 'delivery', 'ifood'],
            'transporte': ['uber', '99', 'taxi', 'ônibus', 'gasolina', 'combustível', 'estacionamento', 'posto', 'carro', 'manutenção'],
            'mercado': ['mercado', 'supermercado', 'extra', 'pão de açúcar', 'compras'],
            'moradia': ['aluguel', 'luz', 'água', 'gas', 'internet', 'condomínio', 'limpeza'],
            'saúde': ['médico', 'consulta', 'farmácia', 'drogaria', 'remédio', 'exame', 'dentista', 'convênio', 'academia'],
            'educação': ['curso', 'livro', 'escola', 'faculdade', 'material', 'estudo'],
            'lazer': ['cinema', 'teatro', 'netflix', 'spotify', 'bar', 'cerveja', 'ingresso', 'festa'],
            'salário': ['salário', 'salario', 'freelance', 'bonificação', 'depósito', 'deposito']
        }
        
        
        self.keyword_to_category = {}
        for category, keywords in self.CATEGORIAS_MAP.items():
            for keyword in keywords:
                self.keyword_to_category[keyword.lower()] = category.capitalize()
                
        number = r'(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?'
        # Regex para valores monetários
        self.PADRAO_MONETARIO = [
            # R$ 1.234,56 ou R$1.234,56 ou R$ 3500,25
            rf'R\$\s*({number})',

            # Números com formato brasileiro seguidos de "reais" (nega lookbehind para não ser parte de outro número)
            rf'(?<![\d\.,])({number})\s*(?:reais?|rs?|conto?)\b',

            # Valores grandes isolados (4+ dígitos) — permite também decimais com , ou .
            rf'(?<![\/\d])\b(\d{{4,}}(?:[.,]\d{{1,2}})?)\b(?![\d\/])',

            # Valores com pontos como separador de milhar + vírgula decimal (ex: 3.500,00)
            r'\b(\d{1,3}(?:\.\d{3})*,\d{1,2})\b',

            # Formato americano (1234.56) — bloqueia ser parte de outro número
            rf'(?<![\d\.,])\b({number})\b(?!\d)',

            # Valores simples (até 3 dígitos) — com negative lookbehind para não pegar "92" de "45.92"
            rf'(?<![\d\.,])\b(\d{{1,3}}(?:,\d{{1,2}})?)\b(?=\s*(?:reais?|rs?|no|na|em|para|pro|$))'
        ]
        
        
        # Palavras que indicam tipos de transação
        self.TIPO_TRANSACAO = {
            'receita': ['recebi', 'salário', 'deposito', 'depósito', 'bonificação', 'cashback', 'vendeu', 'ganhei', 'empréstimo recebido'],
            'transferencia': ['transferi', 'pix', 'mandei', 'enviei'],
            'gasto': ['gastei', 'paguei', 'comprei', 'pagamento']
        }
        
    def normaliza_valor(self, valor_str: str) -> float:
        """Normaliza string monetária para float"""
        texto_limpo = valor_str.strip()

        # Se tem vírgula e pontos, formato brasileiro: pontos=milhar, vírgula=decimal
        if ',' in texto_limpo and '.' in texto_limpo:
            texto_limpo = texto_limpo.replace('.', '').replace(',', '.')
        # Se tem apenas vírgula, pode ser decimal brasileiro
        elif ',' in texto_limpo and texto_limpo.count(',') == 1:
            # Se tem 1-2 dígitos após vírgula, é decimal
            if re.match(r'^\d+,\d{1,2}$', texto_limpo):
                texto_limpo = texto_limpo.replace(',', '.')
            else:
                # Vírgula como separador de milhar (raro, mas acontece)
                texto_limpo = texto_limpo.replace(',', '')
        # Se tem apenas pontos
        elif '.' in texto_limpo:
            # Múltiplos pontos = separadores de milhar
            if texto_limpo.count('.') > 1:
                texto_limpo = texto_limpo.replace('.', '')
            # Um ponto com exatamente 2 dígitos = decimal americano
            elif re.match(r'^\d+\.\d{2}$', texto_limpo):
                pass  # já correto
            else:
                # Ponto único com != 2 casas = separador de milhar
                texto_limpo = texto_limpo.replace('.', '')

        try:
            return float(texto_limpo)
        except ValueError:
            return None
    
    def extrai_valor(self, text: str) -> Tuple[Optional[float], str]:
        """Extrai valor monetário do texto"""
        text = text.lower()
        
        for padrao in self.PADRAO_MONETARIO:
            matches = re.findall(padrao, text, re.IGNORECASE)
            if matches:
                valor_str = matches[0]
                valor = self.normaliza_valor(valor_str)
                if valor is not None and valor > 0:
                    return valor, "regex"
                    
        return None, "none"
    
    def extrai_categoria_keyword(self, text: str) -> Tuple[str, str]:
        """Extrai categoria baseada em keywords"""
        text_lower = text.lower()
        
        # Busca por keywords de categoria
        for keyword, categoria in self.keyword_to_category.items():
            if keyword in text_lower:
                return categoria, "keyword"
                
        return "Outros", "none"
    
    
    
    def extrai_tipo_transacao(self, text: str) -> str:
        """Determina o tipo da transação"""
        text_lower = text.lower()
        
        # Verifica keywords por tipo
        for tipo_de_transacao, keywords in self.TIPO_TRANSACAO.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return tipo_de_transacao
                    
        # Default para gastos se tem valor
        return "gasto"
    
    def extrai_detalhes(self, text: str, amount: Optional[float]) -> Optional[str]:
        """Extrai detalhes adicionais"""
        # Remove valor monetário

        texto_limpo = text
        
        if amount:
            # Remove padrões monetários
            for padrao in self.PADRAO_MONETARIO:
                texto_limpo = re.sub(padrao, '', texto_limpo, flags=re.IGNORECASE)
                
        # Remove preposições e artigos comuns
        texto_limpo = re.sub(r'\b(no|na|em|do|da|o|a|os|as|para|pro|de|com)\b', '', texto_limpo, flags=re.IGNORECASE)
        
        # Remove palavras de ação comuns 
        texto_limpo = re.sub(r'\b(gastei|paguei|comprei|recebi|transferi)\b', '', texto_limpo, flags=re.IGNORECASE)
        
        
        # Limpa espaços extras
        texto_limpo = ' '.join(texto_limpo.split()).strip()
        
        # Se sobrou algo útil, retorna
        if len(texto_limpo) > 2 and texto_limpo != text.lower().strip():
            return texto_limpo
            
        return None
    
    def aplica_extrator(self, text: str) -> Dict[str, Any]:
        amount, amount_source = self.extrai_valor(text)
        category_kw, category_source = self.extrai_categoria_keyword(text)
        tx_type = self.extrai_tipo_transacao(text)
        details = self.extrai_detalhes(text, amount)

        if amount is None:
            tx_type = "desconhecido"

        # previsão do modelo, se injetado
        category_model = None
        model_prob = None
        if self.category_model is not None:
            try:
                category_model, model_prob = self.category_model.predict(text)
            except Exception as e:
                print(f"[ExtratorFinanceiro] Erro ao usar CategoryModel: {e}")
                category_model, model_prob = None, None

        # decisão final de categoria
        final_category = category_model

        # confiança: fatores simples (valor + keyword + modelo + acordo)
        confidence = 0.0
        if amount_source != "none":
            confidence += 0.4
        if category_source != "none":
            confidence += 0.3
        if model_prob is not None:
            confidence += 0.4 * float(model_prob)
        # bônus se concordam
        cat_agreement = False
        if category_model and category_kw and (category_model.strip().lower() == category_kw.strip().lower()):
            cat_agreement = True
            confidence += 0.2

        confidence = min(confidence, 1.0)
        return {
            "raw_text": text,
            "type": tx_type,
            "amount": amount,
            "currency": "BRL" if amount is not None else None,
            "category": final_category,
            "model_confidence": round(model_prob, 3) if model_prob is not None else None,
            "details": details,
            "meta": {
                "amount_source": amount_source,
                "category_source": category_source,
                "confidence": round(confidence, 2),
                "category_agreement": cat_agreement
            }
        }


