# Implementando o extrator rule-based
import re
from datetime import datetime, date
from typing import Tuple, Optional, Dict, Any
import json

class ExtratorFinanceiro:
    """Extrator rule-based para transações financeiras em português"""
    
    def __init__(self):
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
        
        self.PREPOSICOES_LUGARES = ['no', 'na', 'em', 'do', 'da', 'pelo', 'pela']
        
        # Regex para valores monetários
        self.PADRAO_MONETARIO = [
            # R$ 1.234,56 ou R$1.234,56 
            r'R\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)',
            # Números com formato brasileiro seguidos de "reais"
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?)\s*(?:reais?|rs?|conto?)\b',
            # Valores grandes isolados (3+ dígitos)
            r'(?<![\/\d])\b(\d{4,}(?:,\d{1,2})?)\b(?![\d\/])',  # 4+ dígitos isolados
            # Valores com pontos como separador de milhar + vírgula decimal
            r'\b(\d{1,3}(?:\.\d{3})*,\d{1,2})\b',
            # Formato americano
            r'\b(\d+\.\d{2})\b(?!\d)',
            # Valores simples (até 3 dígitos)
            r'\b(\d{1,3}(?:,\d{1,2})?)\b(?=\s*(?:reais?|rs?|no|na|em|para|pro|$))'
        ]
        
        # Regex para datas
        self.PADRAO_DATA = [
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # dd/mm/yyyy
            r'(\d{1,2})/(\d{1,2})',  # dd/mm
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
    
    def extrai_categoria(self, text: str) -> Tuple[str, str]:
        """Extrai categoria baseada em keywords"""
        text_lower = text.lower()
        
        # Busca por keywords de categoria
        for keyword, categoria in self.keyword_to_category.items():
            if keyword in text_lower:
                return categoria, "keyword"
                
        return "Outros", "none"
    
    def extrai_lugar(self, text: str) -> Tuple[Optional[str], str]:
        """Extrai local baseado em heurísticas"""
        text_lower = text.lower()
        
        # Busca por padrões "no/na/em + lugar"
        for prep in self.PREPOSICOES_LUGARES:
            padrao = f'{prep}\\s+(\\w+(?:\\s+\\w+)*?)(?:\\s|$)'
            matches = re.findall(padrao, text_lower)
            if matches:
                lugar = matches[0].strip()
                # Remove artigos comuns
                lugar = re.sub(r'^(o|a|os|as)\\s+', '', lugar)
                if len(lugar) > 2:  # Evita lugares muito pequenos
                    return lugar, "heuristic"
        
        # Busca por nomes próprios 
        texto_original = text
        pronomes_proprios = re.findall(r'\\b[A-Z][a-z]+(?:\\s+[A-Z][a-z]+)*', texto_original)
        if pronomes_proprios:
            # Pega o maior nome próprio
            longest = max(pronomes_proprios, key=len)
            if len(longest) > 3:
                return longest, "heuristic"
                
        return None, "none"
    
    def extrai_data(self, text: str) -> Optional[str]:
        """Extrai data do texto"""
        hoje = date.today()
        
        # Palavras especiais
        if 'hoje' in text.lower():
            return hoje.strftime('%Y-%m-%d')
        elif 'ontem' in text.lower():
            ontem = date(hoje.year, hoje.month, hoje.day - 1)
            return ontem.strftime('%Y-%m-%d')
        
        # Padrões de data
        for padrao in self.PADRAO_DATA:
            matches = re.findall(padrao, text)
            if matches:
                match = matches[0]
                if len(match) == 3:  # dd/mm/yyyy
                    day, month, year = match
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                elif len(match) == 2:  # dd/mm (assume ano atual)
                    day, month = match
                    return f"{hoje.year}-{month.zfill(2)}-{day.zfill(2)}"
                    
        return None
    
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
    
    def extrai_detalhes(self, text: str, amount: Optional[float], place: Optional[str]) -> Optional[str]:
        """Extrai detalhes adicionais"""
        # Remove valor monetário e lugar do texto

        texto_limpo = text
        
        if amount:
            # Remove padrões monetários
            for padrao in self.PADRAO_MONETARIO:
                texto_limpo = re.sub(padrao, '', texto_limpo, flags=re.IGNORECASE)
                
        if place:
            texto_limpo = texto_limpo.replace(place, '')
            
        # Remove preposições e artigos comuns
        texto_limpo = re.sub(r'\\b(no|na|em|do|da|o|a|os|as|para|pro|de|com)\\b', '', texto_limpo, flags=re.IGNORECASE)
        
        # Remove palavras de ação comuns
        texto_limpo = re.sub(r'\\b(gastei|paguei|comprei|recebi|transferi)\\b', '', texto_limpo, flags=re.IGNORECASE)
        
        # Limpa espaços extras
        texto_limpo = ' '.join(texto_limpo.split()).strip()
        
        # Se sobrou algo útil, retorna
        if len(texto_limpo) > 2 and texto_limpo != text.lower().strip():
            return texto_limpo
            
        return None
    
    def aplica_extrator(self, text: str) -> Dict[str, Any]:
        """Função unificada que extrai todos os campos estruturados"""
        
        # Extrações principais
        amount, amount_source = self.extrai_valor(text)
        category, category_source = self.extrai_categoria(text)
        place, place_source = self.extrai_lugar(text)
        date_extracted = self.extrai_data(text)
        transaction_type = self.extrai_tipo_transacao(text)
        details = self.extrai_detalhes(text, amount, place)
        
        # Se não tem valor, marca como desconhecido
        if amount is None:
            transaction_type = "desconhecido"
        
        # Calcula confiança baseada nas extrações bem-sucedidas
        confidence_factors = []
        if amount_source != "none": confidence_factors.append(0.4)
        if category_source != "none": confidence_factors.append(0.3)
        if place_source != "none": confidence_factors.append(0.2)
        if date_extracted: confidence_factors.append(0.1)
        
        confidence = sum(confidence_factors) if confidence_factors else 0.3
        confidence = min(confidence, 1.0)  # Cap at 1.0
        
        return {
            "raw_text": text,
            "type": transaction_type,
            "amount": amount,
            "currency": "BRL" if amount is not None else None,
            "category": category,
            "place": place,
            "details": details,
            "date": date_extracted,
            "meta": {
                "amount_source": amount_source,
                "category_source": category_source,
                "place_source": place_source,
                "confidence": round(confidence, 2)
            }
        }

