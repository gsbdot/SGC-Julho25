from flask import Blueprint, render_template
from flask_login import login_required

# 1. Cria o Blueprint (o "capítulo")
# O primeiro argumento 'sobre' é o nome do blueprint.
# O segundo, __name__, ajuda o Flask a localizar o arquivo.
sobre_bp = Blueprint('sobre', __name__)

# 2. Cria a rota dentro do Blueprint
@sobre_bp.route('/sobre')
@login_required
def sobre():
    """Renderiza a página 'Sobre o Sistema'."""
    # 3. A função simplesmente renderiza um novo template que criaremos a seguir
    return render_template('sobre.html', titulo_pagina="Sobre o Sistema")