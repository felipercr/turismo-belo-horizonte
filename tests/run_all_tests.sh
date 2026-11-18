#!/bin/bash

echo "EXEUTANDO TESTES DE UNIDADE"
cd "unit_tests"
python test_db_methods.py

echo "EXECUTANDO TESTES DE INTEGRACAO"
echo "ATENCAO: O servidor já deve estar rodando..."
cd "../integration_tests"
python test_db_integration.py