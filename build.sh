#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala as dependências do Python
pip install -r requirements.txt

# Executa as migrações do banco de dados para criar/atualizar as tabelas
flask db upgrade

# Executa nosso novo comando para criar o admin inicial (se não existir)
flask init-db
