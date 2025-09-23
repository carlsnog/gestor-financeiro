import pytest
import json
from registrador.Extrator import ExtratorFinanceiro

class TestExtratorFinanceiro:
    """Testes unitários para o ExtratorFinanceiro"""

    def setup_method(self):
        """Setup executado antes de cada teste"""
        self.extrator = ExtratorFinanceiro()

    def test_normaliza_valor_brazilian_format(self):
        """Testa normalização de valores no formato brasileiro"""
        assert self.extrator.normaliza_valor("1.500,00") == 1500.0
        assert self.extrator.normaliza_valor("23,50") == 23.5
        assert self.extrator.normaliza_valor("1.234.567,89") == 1234567.89
        assert self.extrator.normaliza_valor("10,5") == 10.5

    def test_normaliza_valor_simple_numbers(self):
        """Testa normalização de números simples"""
        assert self.extrator.normaliza_valor("4200") == 4200.0
        assert self.extrator.normaliza_valor("500") == 500.0
        assert self.extrator.normaliza_valor("15") == 15.0

    def test_normaliza_valor_american_format(self):
        """Testa normalização de valores no formato americano"""
        assert self.extrator.normaliza_valor("1234.56") == 1234.56
        assert self.extrator.normaliza_valor("29.90") == 29.90

    def test_extrai_valor_with_reais(self):
        """Testa extração de valores seguidos de 'reais'"""
        valor, source = self.extrator.extrai_valor("5 reais num pastel")
        assert valor == 5.0
        assert source == "regex"

        valor, source = self.extrator.extrai_valor("200 reais na farmácia") 
        assert valor == 200.0
        assert source == "regex"
       
        valor, source = self.extrator.extrai_valor("Táxi até em casa 45.92 reais") 
        assert valor == 45.92
        assert source == "regex"
        

    def test_extrai_valor_with_rs_symbol(self):
        """Testa extração de valores com símbolo R$"""
        valor, source = self.extrator.extrai_valor("R$ 23,50 no mercado")
        assert valor == 23.5
        assert source == "regex"

        valor, source = self.extrator.extrai_valor("R$150 consulta médica")
        assert valor == 150.0
        assert source == "regex"

    def test_extrai_valor_large_numbers(self):
        """Testa extração de valores grandes"""
        valor, source = self.extrator.extrai_valor("Paguei 1.500,00 de aluguel")
        assert valor == 1500.0
        assert source == "regex"

        valor, source = self.extrator.extrai_valor("Recebi R$ 3500,25 de salário")
        assert valor == 3500.25

        valor, source = self.extrator.extrai_valor("Salário 15/09 4200")
        assert valor == 4200.0  
        assert source == "regex"

    def test_extrai_valor_no_value(self):
        """Testa casos onde não há valor monetário"""
        valor, source = self.extrator.extrai_valor("Comprei um café hoje")
        assert valor is None
        assert source == "none"

    def test_extrai_categoria_food(self):
        """Testa extração de categoria Comida"""
        categoria, source = self.extrator.extrai_categoria("5 reais num pastel")
        assert categoria == "Comida"
        assert source == "keyword"

        categoria, source = self.extrator.extrai_categoria("Pizza delivery 42,90")
        assert categoria == "Comida"
        assert source == "keyword"

    def test_extrai_categoria_transport(self):
        """Testa extração de categoria Transporte"""
        categoria, source = self.extrator.extrai_categoria("13 reais em uber")
        assert categoria == "Transporte"
        assert source == "keyword"

        categoria, source = self.extrator.extrai_categoria("Gasolina posto Shell 120")
        assert categoria == "Transporte"
        assert source == "keyword"

    def test_extrai_categoria_health(self):
        """Testa extração de categoria Saúde"""
        categoria, source = self.extrator.extrai_categoria("R$150 consulta médica")
        assert categoria == "Saúde"
        assert source == "keyword"

        categoria, source = self.extrator.extrai_categoria("200 reais na farmácia")
        assert categoria == "Saúde"
        assert source == "keyword"

    def test_extrai_categoria_salary(self):
        """Testa extração de categoria Salário"""
        categoria, source = self.extrator.extrai_categoria("Salário 15/09 4200")
        assert categoria == "Salário"
        assert source == "keyword"

        categoria, source = self.extrator.extrai_categoria("Depósito salário 02/09 3500")
        assert categoria == "Salário"
        assert source == "keyword"

    def test_extrai_categoria_default(self):
        """Testa categoria padrão quando não encontra keywords"""
        categoria, source = self.extrator.extrai_categoria("Cortei o cabelo 35 reais")
        assert categoria == "Outros"
        assert source == "none"


    def test_extrai_tipo_transacao_expense(self):
        """Testa detecção de gastos"""
        transaction_type = self.extrator.extrai_tipo_transacao("Paguei 1.500,00 de aluguel")
        assert transaction_type == "gasto"

        transaction_type = self.extrator.extrai_tipo_transacao("Gastei R$ 80 na farmácia")
        assert transaction_type == "gasto"

    def test_extrai_tipo_transacao_income(self):
        """Testa detecção de receitas"""  
        transaction_type = self.extrator.extrai_tipo_transacao("Recebi R$ 2500 freelance")
        assert transaction_type == "receita"

        transaction_type = self.extrator.extrai_tipo_transacao("Salário 15/09 4200")
        assert transaction_type == "receita"

    def test_extrai_tipo_transacao_transfer(self):
        """Testa detecção de transferências"""
        transaction_type = self.extrator.extrai_tipo_transacao("Transferi R$ 500 para minha mãe")
        assert transaction_type == "transferencia"

        transaction_type = self.extrator.extrai_tipo_transacao("Pix de 100 reais pro João")
        assert transaction_type == "transferencia"




    def test_aplica_extrator_complete_example(self):
        """Testa extração estruturada completa"""
        text = "R$ 23,50 no mercado"
        result = self.extrator.aplica_extrator(text)

        assert result["raw_text"] == text
        assert result["amount"] == 23.5
        assert result["currency"] == "BRL"
        assert result["category"] == "Mercado"
        assert result["type"] == "gasto"
        assert result["meta"]["amount_source"] == "regex"
        assert result["meta"]["category_source"] == "keyword"

    def test_aplica_extrator_no_amount(self):
        """Testa extração quando não há valor"""
        text = "Comprei um café hoje"
        result = self.extrator.aplica_extrator(text)

        assert result["raw_text"] == text
        assert result["amount"] is None
        assert result["currency"] is None
        assert result["type"] == "desconhecido"
        assert result["category"] == "Comida"  # Deveria reconhecer café
        assert result["meta"]["amount_source"] == "none"

    def test_base_examples_from_problem(self):
        """Testa os 5 exemplos base fornecidos no problema"""

        # Exemplo 1: 5 reais num pastel
        result = self.extrator.aplica_extrator("5 reais num pastel")
        assert result["amount"] == 5.0
        assert result["category"] == "Comida"

        # Exemplo 2: 13 reais em uber de casa para shopping  
        result = self.extrator.aplica_extrator("13 reais em uber de casa para shopping")
        assert result["amount"] == 13.0
        assert result["category"] == "Transporte"

        # Exemplo 3: 50 reais no jantar bodega rainha
        result = self.extrator.aplica_extrator("50 reais no jantar bodega rainha")
        assert result["amount"] == 50.0
        assert result["category"] == "Comida"

        # Exemplo 4: Depósito salário 02/09 3500
        result = self.extrator.aplica_extrator("Depósito salário 02/09 3500")
        assert result["amount"] == 3500.0
        assert result["category"] == "Salário"
        assert result["type"] == "receita"

        # Exemplo 5: Paguei R$ 40 no posto de gasolina
        result = self.extrator.aplica_extrator("Paguei R$ 40 no posto de gasolina")
        assert result["amount"] == 40.0
        assert result["category"] == "Transporte"
        assert result["type"] == "gasto"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
