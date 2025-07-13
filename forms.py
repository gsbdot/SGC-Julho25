# Início do arquivo completo: forms.py

from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, IntegerField, DateField, 
                     SubmitField, FloatField, SelectField, BooleanField, 
                     HiddenField, PasswordField, FieldList, FormField, FileField)
from wtforms.validators import (DataRequired, Length, Optional, NumberRange, 
                                ValidationError, Email, EqualTo, Regexp)
from wtforms import Form as WTForm_Form
from datetime import date
import math

# --- Imports dos Modelos e do QuerySelectField ---
from models import Ata, ItemAta, UnidadeSaude, Fornecedor, Processo
from wtforms_sqlalchemy.fields import QuerySelectField

# --- Funções de consulta para os SelectFields ---
def get_fornecedores():
    return Fornecedor.query.order_by(Fornecedor.nome_fantasia).all()

def get_processos():
    return Processo.query.order_by(Processo.ano.desc(), Processo.numero_processo.desc()).all()

def coerce_int_or_none(x):
    if x is None or str(x).strip() == '': return None
    try: return int(x)
    except ValueError: raise ValidationError('Valor inválido para seleção.')

DATE_FORMATS = ['%Y-%m-%d', '%d/%m/%Y']

class BrazilianFloatField(FloatField):
    def process_formdata(self, valuelist):
        if valuelist:
            raw_value = str(valuelist[0])
            if raw_value and raw_value.strip():
                cleaned_value = raw_value.replace('.', '').replace(',', '.')
                try:
                    self.data = float(cleaned_value)
                except ValueError:
                    self.data = None 
                    raise ValueError(self.gettext('Não é um valor decimal válido.'))
            else:
                self.data = None
        else:
            self.data = None

# --- Formulários de Autenticação e Usuário ---
class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    submit = SubmitField('Entrar')

# --- Formulário de Fornecedor ---
class FornecedorForm(FlaskForm):
    nome_fantasia = StringField('Nome Fantasia', validators=[DataRequired(), Length(min=2, max=200)])
    razao_social = StringField('Razão Social (Opcional)', validators=[Optional(), Length(max=200)])
    # --- ATUALIZAÇÃO: Regex e Validação do CNPJ ---
    cnpj = StringField('CNPJ', validators=[
        DataRequired(),
        Length(min=14, max=18),
        # Regex atualizado para aceitar letras e números
        Regexp(r'^[A-Za-z0-9]{2}\.?[A-Za-z0-9]{3}\.?[A-Za-z0-9]{3}/?[A-Za-z0-9]{4}-?[A-Za-z0-9]{2}$', message='Formato de CNPJ inválido.')
    ])
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    email = StringField('E-mail', validators=[Optional(), Email(message="Email inválido."), Length(max=120)])
    submit = SubmitField('Salvar Fornecedor')

    def validate_cnpj(self, cnpj_field):
        # Limpa o CNPJ para um formato padrão, removendo apenas os caracteres de formatação
        cleaned_cnpj = cnpj_field.data.replace('.', '').replace('/', '').replace('-', '')
        
        query = Fornecedor.query.filter_by(cnpj=cleaned_cnpj)
        
        # Se for edição, exclui o próprio objeto da verificação
        if self.id.data:
            query = query.filter(Fornecedor.id != int(self.id.data))
        
        if query.first():
            raise ValidationError('Este CNPJ já está cadastrado no sistema.')
            
        # Garante que o dado salvo no banco estará limpo
        self.cnpj.data = cleaned_cnpj

    id = HiddenField()


# --- Formulário Processo ---
class ProcessoForm(FlaskForm):
    numero_processo = StringField('Número do Processo', validators=[DataRequired(), Length(max=100)])
    ano = IntegerField('Ano do Processo', validators=[DataRequired(), NumberRange(min=1990, max=2100)])
    descricao = TextAreaField('Descrição/Objeto do Processo', validators=[Optional()])
    submit = SubmitField('Salvar Processo')
    id = HiddenField() # Usado para edição

    def validate(self, extra_validators=None):
        initial_validation = super(ProcessoForm, self).validate(extra_validators)
        if not initial_validation:
            return False
        
        query = Processo.query.filter_by(numero_processo=self.numero_processo.data, ano=self.ano.data)
        
        if self.id.data:
            query = query.filter(Processo.id != int(self.id.data))

        if query.first():
            self.numero_processo.errors.append("Já existe um processo com este número e ano.")
            return False
            
        return True

# --- Formulários de Documentos ---
class AtaForm(FlaskForm):
    numero_ata = StringField('Número da Ata', validators=[DataRequired(), Length(min=1, max=100)])
    ano = IntegerField('Ano da Ata', validators=[DataRequired()])
    descricao = TextAreaField('Descrição', validators=[Optional()])
    
    fornecedor_rel = QuerySelectField(
        'Fornecedor',
        query_factory=get_fornecedores,
        get_label='nome_fantasia',
        allow_blank=True,
        blank_text='-- Selecione um Fornecedor --',
        validators=[Optional()]
    )
    
    processo = QuerySelectField('Processo Vinculado (Opcional)',
        query_factory=get_processos,
        get_label=lambda p: f"{p.numero_processo}/{p.ano}",
        allow_blank=True,
        blank_text='-- Nenhum Processo --',
        validators=[Optional()])

    data_assinatura = DateField('Data de Assinatura', format=DATE_FORMATS, validators=[Optional()])
    data_validade = DateField('Data de Validade', format=DATE_FORMATS, validators=[Optional()])
    submit = SubmitField('Salvar Ata')

class ItemAtaLoteSubForm(WTForm_Form):
    descricao_item = StringField('Descrição do Item', validators=[DataRequired()])
    tipo_item = SelectField('Tipo do Item', choices=ItemAta.TIPO_ITEM_CHOICES, validators=[DataRequired()])
    unidade_medida = StringField('Unidade de Medida', validators=[Optional(), Length(max=50)])
    quantidade_registrada = BrazilianFloatField('Qtd. Registrada', validators=[DataRequired(), NumberRange(min=0.000001, message="Qtd. deve ser positiva.")])
    valor_unitario_registrado = BrazilianFloatField('Valor Unitário (R$)', validators=[Optional(), NumberRange(min=0)])
    lote = StringField('Lote', validators=[Optional(), Length(max=100)])

class AdicionarItensLoteAtaForm(FlaskForm):
    itens_ata = FieldList(FormField(ItemAtaLoteSubForm), min_entries=1, max_entries=30)
    submit = SubmitField('Adicionar Itens à Ata')

class ItemAtaForm(FlaskForm): 
    descricao_item = StringField('Descrição do Item', validators=[DataRequired()])
    tipo_item = SelectField('Tipo do Item', choices=ItemAta.TIPO_ITEM_CHOICES, validators=[DataRequired()])
    unidade_medida = StringField('Unidade de Medida', validators=[Optional(), Length(max=50)])
    quantidade_registrada = BrazilianFloatField('Qtd. Registrada na Ata', validators=[DataRequired(), NumberRange(min=0)])
    valor_unitario_registrado = BrazilianFloatField('Valor Unitário (R$)', validators=[Optional(), NumberRange(min=0)])
    lote = StringField('Lote', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Salvar Item da Ata')

class UnidadeSaudeForm(FlaskForm):
    nome_unidade = StringField('Nome da Unidade', validators=[DataRequired(), Length(max=150)])
    tipo_unidade = SelectField('Tipo da Unidade', choices=UnidadeSaude.TIPO_UNIDADE_CHOICES, validators=[DataRequired(message="Selecione um tipo válido.")])
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    telefone = StringField('Telefone', validators=[Optional(), Length(max=20)])
    email_responsavel = StringField('Email do Responsável', validators=[Optional(), Email(message="Email inválido."), Length(max=120)])
    submit = SubmitField('Salvar Unidade de Saúde')

class ItemLivreContratoSubForm(WTForm_Form):
    descricao = StringField('Descrição do Item', validators=[DataRequired(message="Descrição do item é obrigatória.")])
    unidade_medida = StringField('Unidade', validators=[Optional(), Length(max=50)])
    quantidade = BrazilianFloatField('Quantidade', validators=[DataRequired(message="Quantidade é obrigatória."), NumberRange(min=0.000001, message="Quantidade deve ser positiva.")])
    valor_unitario = BrazilianFloatField('Valor Unitário (R$)', validators=[DataRequired(message="Valor unitário é obrigatório."), NumberRange(min=0)]) 

class ContratoForm(FlaskForm): 
    numero_contrato = StringField('Número do Contrato', validators=[DataRequired(), Length(min=1, max=100)])
    objeto = TextAreaField('Objeto do Contrato', validators=[DataRequired()])
    unidade_saude_responsavel = QuerySelectField('Unidade de Saúde Responsável (Opcional)', query_factory=lambda: UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade), get_label='nome_unidade', allow_blank=True, blank_text='-- Nenhuma (Geral) --', validators=[Optional()])
    
    fornecedor_rel = QuerySelectField('Fornecedor', query_factory=get_fornecedores, get_label='nome_fantasia', allow_blank=False, validators=[DataRequired(message="Selecione um fornecedor.")])
    
    processo = QuerySelectField('Processo Vinculado (Opcional)',
        query_factory=get_processos,
        get_label=lambda p: f"{p.numero_processo}/{p.ano}",
        allow_blank=True,
        blank_text='-- Nenhum Processo --',
        validators=[Optional()])

    data_assinatura_contrato = DateField('Data de Assinatura', format=DATE_FORMATS, validators=[Optional()])
    data_inicio_vigencia = DateField('Início da Vigência', format=DATE_FORMATS, validators=[Optional()])
    data_fim_vigencia_original = DateField('Fim da Vigência Original', format=DATE_FORMATS, validators=[Optional()])
    itens_contratados = FieldList(FormField(ItemLivreContratoSubForm), min_entries=1, max_entries=50)
    submit = SubmitField('Salvar Contrato')

class AditivoForm(FlaskForm):
    numero_aditivo = StringField('Número do Termo Aditivo', validators=[DataRequired(), Length(max=100)])
    data_assinatura = DateField('Data de Assinatura', format=DATE_FORMATS, validators=[DataRequired()])
    objeto = TextAreaField('Objeto do Aditivo', validators=[Optional()])
    valor_acrescimo = BrazilianFloatField('Acréscimo de Valor (R$)', validators=[Optional()], description="Use valor negativo para decréscimo. Ex: -500,00")
    prazo_adicional_dias = IntegerField('Prazo Adicional (dias)', validators=[Optional()], description="Use valor negativo para redução de prazo.")
    nova_data_fim_vigencia = DateField('Ou Nova Data Final de Vigência', format=DATE_FORMATS, validators=[Optional()], description="Preencha para definir uma data final exata.")
    submit = SubmitField('Salvar Termo Aditivo')

class ConsumoItemSubFormulario(WTForm_Form): 
    item_ata_id = SelectField('Item da Ata', coerce=coerce_int_or_none, validators=[DataRequired(message="Item é obrigatório.")])
    quantidade_consumida = BrazilianFloatField('Quantidade Consumida', validators=[DataRequired(message="Qtd. é obrigatória."), NumberRange(min=0.000001, message="Qtd. deve ser positiva.")])

class ContratinhoForm(FlaskForm):
    numero_contratinho = StringField('Número do Contratinho/Doc.', validators=[DataRequired(), Length(max=100)])
    objeto = TextAreaField('Objeto Geral (Opcional)', validators=[Optional()])
    
    fornecedor_rel = QuerySelectField('Favorecido/Fornecedor', query_factory=get_fornecedores, get_label='nome_fantasia', allow_blank=False, validators=[DataRequired(message="Selecione um fornecedor.")])
    
    processo = QuerySelectField('Processo Vinculado (Opcional)',
        query_factory=get_processos,
        get_label=lambda p: f"{p.numero_processo}/{p.ano}",
        allow_blank=True,
        blank_text='-- Nenhum Processo --',
        validators=[Optional()])

    data_emissao = DateField('Data de Emissão', format=DATE_FORMATS, validators=[DataRequired()])
    data_fim_vigencia = DateField('Data Fim de Vigência (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    ata_id = QuerySelectField('Ata Vinculada', query_factory=lambda: Ata.query.order_by(Ata.ano.desc(), Ata.numero_ata.desc()), get_label=lambda a: f"{a.numero_ata}/{a.ano}", allow_blank=False, validators=[DataRequired(message="Selecione uma Ata.")])
    unidade_saude_id = QuerySelectField('Unidade de Saúde Destino', query_factory=lambda: UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade), get_label='nome_unidade', allow_blank=False, validators=[DataRequired(message="Selecione uma Unidade.")])
    valor_total_manual = BrazilianFloatField('Valor Total Manual (Opcional)', validators=[Optional(), NumberRange(min=0)])
    itens_consumidos = FieldList(FormField(ConsumoItemSubFormulario), min_entries=1, max_entries=20) 
    submit = SubmitField('Salvar Contratinho')

class EmpenhoForm(FlaskForm):
    numero_empenho = StringField('Número do Empenho', validators=[DataRequired(), Length(max=100)])
    descricao_simples = TextAreaField('Descrição Simplificada (Opcional)', validators=[Optional()])

    fornecedor_rel = QuerySelectField('Favorecido/Fornecedor', query_factory=get_fornecedores, get_label='nome_fantasia', allow_blank=False, validators=[DataRequired(message="Selecione um fornecedor.")])
    
    processo = QuerySelectField('Processo Vinculado (Opcional)',
        query_factory=get_processos,
        get_label=lambda p: f"{p.numero_processo}/{p.ano}",
        allow_blank=True,
        blank_text='-- Nenhum Processo --',
        validators=[Optional()])

    data_emissao = DateField('Data de Emissão', format=DATE_FORMATS, validators=[DataRequired()])
    data_fim_vigencia = DateField('Data Fim de Vigência (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    ata_id = QuerySelectField('Ata Vinculada', query_factory=lambda: Ata.query.order_by(Ata.ano.desc(), Ata.numero_ata.desc()), get_label=lambda a: f"{a.numero_ata}/{a.ano}", allow_blank=False, validators=[DataRequired(message="Selecione uma Ata.")])
    unidade_saude_id = QuerySelectField('Unidade de Saúde Destino', query_factory=lambda: UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade), get_label='nome_unidade', allow_blank=False, validators=[DataRequired(message="Selecione uma Unidade.")])
    valor_total_manual = BrazilianFloatField('Valor Total Manual (Opcional)', validators=[Optional(), NumberRange(min=0)])
    itens_consumidos = FieldList(FormField(ConsumoItemSubFormulario), min_entries=1, max_entries=20)
    submit = SubmitField('Salvar Empenho')

# --- Formulários de Relatório ---
class RelatorioPorFornecedorForm(FlaskForm):
    fornecedor = QuerySelectField('Selecione o Fornecedor', query_factory=get_fornecedores, get_label='nome_fantasia', allow_blank=False, validators=[DataRequired()])
    submit = SubmitField('Gerar Relatório PDF')

class RelatorioContratosVigentesUnidadeForm(FlaskForm):
    unidade_saude_id = QuerySelectField('Unidade de Saúde', query_factory=lambda: UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade), get_label='nome_unidade', allow_blank=False, validators=[DataRequired(message="Selecione uma Unidade.")])
    submit = SubmitField('Gerar Relatório')

class RelatorioConsumoUnidadeForm(FlaskForm):
    unidade_saude_id = QuerySelectField('Unidade de Saúde', query_factory=lambda: UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade), get_label='nome_unidade', allow_blank=False, validators=[DataRequired(message="Selecione uma Unidade.")])
    data_inicio = DateField('Data Início (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    data_fim = DateField('Data Fim (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    submit = SubmitField('Gerar Relatório')

class RelatorioConsumoPorItemForm(FlaskForm):
    item_ata_id = QuerySelectField('Item da Ata Específico', query_factory=lambda: ItemAta.query.join(Ata).order_by(Ata.ano.desc(), Ata.numero_ata.desc(), ItemAta.descricao_item), get_label=lambda i: f"{i.descricao_item} (Ata: {i.ata_mae.numero_ata}/{i.ata_mae.ano})", allow_blank=False, validators=[DataRequired()])
    data_inicio = DateField('Data Início (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    data_fim = DateField('Data Fim (Opcional)', format=DATE_FORMATS, validators=[Optional()])
    submit = SubmitField('Gerar Relatório')

class RelatorioPotencialDeSolicitacaoForm(FlaskForm):
    unidade_saude_id = QuerySelectField('Unidade de Saúde', query_factory=lambda: UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade), get_label='nome_unidade', allow_blank=False, validators=[DataRequired(message="Selecione uma Unidade.")])
    submit = SubmitField('Gerar Relatório')
    
# --- Demais Formulários ---
class ImportCSVForm(FlaskForm):
    csv_file = FileField('Arquivo CSV', validators=[DataRequired(message="Por favor, selecione um arquivo.")])
    submit = SubmitField('Importar')

class CotaUnidadeSubForm(WTForm_Form):
    unidade_saude_id = HiddenField()
    quantidade_prevista = BrazilianFloatField('Cota', validators=[Optional(), NumberRange(min=0)])

class GerenciarCotasForm(FlaskForm):
    cotas = FieldList(FormField(CotaUnidadeSubForm))
    submit = SubmitField('Salvar Cotas')

class UserCreationForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('password', message='As senhas devem ser iguais.')])
    role = SelectField('Nível de Acesso (Role)', choices=[('admin', 'Administrador'), ('gestor', 'Gestor de Unidade'), ('leitura', 'Apenas Leitura')], validators=[DataRequired()])
    unidade_saude_id = QuerySelectField('Vincular à Unidade de Saúde (Opcional)', query_factory=lambda: UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade), get_label='nome_unidade', allow_blank=True, blank_text='-- Nenhuma --', validators=[Optional()])
    submit = SubmitField('Criar Usuário')

class UserEditForm(FlaskForm):
    username = StringField('Nome de Usuário', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Nova Senha (Opcional)', validators=[Optional(), Length(min=6, message='A senha deve ter no mínimo 6 caracteres.')])
    password2 = PasswordField('Confirmar Nova Senha', validators=[EqualTo('password', message='As senhas devem ser iguais.')])
    role = SelectField('Nível de Acesso (Role)', choices=[('admin', 'Administrador'), ('gestor', 'Gestor de Unidade'), ('leitura', 'Apenas Leitura')], validators=[DataRequired()])
    unidade_saude_id = QuerySelectField('Vincular à Unidade de Saúde (Opcional)', query_factory=lambda: UnidadeSaude.query.order_by(UnidadeSaude.nome_unidade), get_label='nome_unidade', allow_blank=True, blank_text='-- Nenhuma --', validators=[Optional()])
    submit = SubmitField('Salvar Alterações')

    def __init__(self, original_username=None, *args, **kwargs):
        super(UserEditForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            # Importa o modelo User aqui dentro para evitar importação circular
            from models import User
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Este nome de usuário já está em uso. Por favor, escolha outro.')

class CommentForm(FlaskForm):
    content = TextAreaField('Comentário', validators=[DataRequired(), Length(min=1, max=1000)])
    submit = SubmitField('Enviar Comentário')

# Fim do arquivo completo: forms.py