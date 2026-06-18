import datetime, os, re, requests
from database import db
from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask, request, jsonify
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from waitress import serve

from user import Usuario
from log import Log
from colaborador import Colaborador
from colaborador_departamento import ColaboradorDepartamento
from departamento import Departamento
from empresa import Empresa
from acesso_externo import AcessoExterno
from financeiro import Financeiro
from menu import Menu
from pagina import Pagina
from colaborador_empresa import ColaboradorEmpresa
from cliente import ApiCliente
from centrocusto import CentroCusto
from colaborador_acesso import ColaboradorAcesso
from cliente_hotspot import HotspotClient
from hotspot_local import HotspotLocal
from hotspot_termos import HotspotTermos
from usuario_empresa import UsuarioEmpresa
from nivel_acesso import NivelAcesso
from ordem_servico import OrdemServico
from movimentacao_os import MovimentacaoOS
from modelo_os import ModeloOS
from agendamento_os import OSAgendamento
from visto_avisos import VistoAvisos
from aviso_os import AvisoOS

load_dotenv()

# FUNÇÕES AUXILIARES

# Converte string DD/MM/YYYY em objeto date do Python
def f_validar_data(v_str_data):
    try:
        if not v_str_data: return None
        return datetime.datetime.strptime(v_str_data, '%d/%m/%Y').date()
    except (ValueError, TypeError): 
        return None

# Converte string HH:MM:SS em objeto time do Python
def f_validar_hora(v_str_hora):
    try:
        if not v_str_hora: return None
        return datetime.datetime.strptime(v_str_hora, '%H:%M:%S').time()
    except (ValueError, TypeError): 
        return None

# FUNÇÃO PRINCIPAL

def create_app(config_override=None):
  v_app = Flask(__name__)

  db_uri = (
      f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
      f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
  )
  v_app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
  v_app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

  if config_override:
    v_app.config.update(config_override)

  db.init_app(v_app)
  swagger = Swagger(v_app)

  v_login_manager = LoginManager()
  v_login_manager.init_app(v_app)

  @v_login_manager.user_loader
  def f_load_user(v_user_id):
      return db.session.get(Usuario, int(v_user_id))

  # ENDPOINTS DE USUÁRIO

  @v_app.route('/Usuario/add', methods=['POST'])
  def f_create_user():
      """
      Cadastra um novo usuário
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: Usuario
            required:
              - nome
              - email
              - senha
              - nivel
              - estado
            properties:
              nome:
                type: string
                example: "João Silva"
              telefone:
                type: string
                example: "40028922"
              celular:
                type: string
                example: "40028922"
              fax:
                type: string
                example: "40028922"
              cpfcnpj:
                type: string
                example: "123.456.789-00"
              rgie:
                type: string
                example: "12.345.678-9"
              tipo:
                type: string
                example: "exemplo"
              email:
                type: string
                example: "joao@gmail.com"
              senha:
                type: string
                example: "senhainicial"
              datanascimento:
                type: string
                example: "20/06/2005"
              nivel:
                type: integer
                example: 1
              estado:
                type: boolean
                example: true
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido ou malformado"}), 400

      v_campos_obrigatorios = ['nome', 'email', 'senha', 'nivel', 'estado']
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

      if v_invalidos:
          # Retorna erro 400 informando o usuário que faltam campos obrigatórios
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios!"
          }), 400
      
      if not isinstance(v_dados.get('nivel'), int):
        return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'nivel' deve ser um número inteiro"}), 400
        
      if not isinstance(v_dados.get('estado'), bool):
        return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'estado' deve ser booleano (true/false)"}), 400
  
      v_data_nasc_str = v_dados.get('datanascimento')
      if v_data_nasc_str:
          v_data_objeto = f_validar_data(v_data_nasc_str)
          if not v_data_objeto:
              return jsonify({"erro": "Formato inválido", "mensagem": "datanascimento deve ser DD/MM/YYYY"}), 400
          v_dados['datanascimento'] = v_data_objeto

      v_senha_pura = v_dados.pop('senha', None)
      v_novo_usuario = Usuario(**v_dados)
      # Usa a função de hash definida em user.py
      v_novo_usuario.f_definir_senha(v_senha_pura)
        
      try:
          db.session.add(v_novo_usuario)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_novo_usuario.id}), 201
      except (TypeError, ValueError) as e:
          db.session.rollback()
          return jsonify({
              "erro": "Tipo de dado inválido", 
              "mensagem": "Um ou mais campos possuem valores incompatíveis com o banco de dados"
          }), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)
          # Verifica se o email fornecido já está cadastrado
          if 'Duplicate entry' in v_erro_str or 'UNIQUE constraint failed' in v_erro_str:
              return jsonify({
                  "erro": "Conflito de dados",
                  "mensagem": f"O email '{v_dados.get('email')}' já está cadastrado"
              }), 409
          return jsonify({"erro": "Erro de integridade", "detalhes": str(e.orig)}), 400     
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Usuario/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_user(id):
      """
      Busca um usuário pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID único do usuário
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_usuario = db.session.get(Usuario, id)

          if not v_usuario:
              return jsonify({"erro": "Não encontrado"}), 404
          
          return jsonify(v_usuario.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro de banco de dados", "mensagem": "Não foi possível conectar ao servidor"}), 503

  @v_app.route('/Usuario/get', methods=['GET'])
  @login_required
  def f_read_all_users():
      """
      Busca todos os usuários cadastrados
      ---
      responses:
        200:
          description:
        503:
          description:
      """
      try:
          v_usuarios = Usuario.query.all()
          
          v_lista_usuarios = [v_u.f_para_dicionario() for v_u in v_usuarios]
          
          return jsonify(v_lista_usuarios), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível recuperar a lista de usuários"
          }), 503

  @v_app.route('/Usuario/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_user(id):
      """
      Atualiza dados de um usuário existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              nome:
                type: string
                example: "João Editado"
              telefone:
                type: string
                example: "89224002"
              celular:
                type: string
                example: "89224002"
              fax:
                type: string
                example: "89224002"
              cpfcnpj:
                type: string
                example: "987.654.321-00"
              rgie:
                type: string
                example: "98.765.432-1"
              tipo:
                type: string
                example: "example"
              email:
                type: string
                example: "novoemaildojoao@gmail.com"
              senha:
                type: string
                example: "senhanova"
              datanascimento:
                type: string
                example: "21/06/2005"
              nivel:
                type: integer
                example: 2
              estado:
                type: boolean
                example: false
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_usuario = db.session.get(Usuario, id)

      if not v_usuario:
          return jsonify({"erro": "Não encontrado"}), 404
      
      v_novos_dados = request.get_json(silent=True)
      if v_novos_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400
      
      v_campos_permitidos = ['nome', 'telefone', 'celular', 'fax', 'cpfcnpj', 'rgie', 'tipo', 'email', 'senha', 'datanascimento', 'nivel', 'estado']

      try:
          for v_chave, v_valor in v_novos_dados.items():
            if v_chave in v_campos_permitidos:
                if v_chave == 'nivel' and not isinstance(v_valor, int):
                    raise TypeError("O campo nivel deve ser um número inteiro")
                # Se a chave enviada no JSON for senha, aplica o hash antes de salvar
                if v_chave == 'senha':
                    v_usuario.f_definir_senha(v_valor)
                elif v_chave == 'datanascimento' and v_valor:
                  v_data_objeto = f_validar_data(v_valor)
                  if not v_data_objeto:
                      return jsonify({"erro": "Data inválida", "mensagem": "Use DD/MM/YYYY"}), 400
                  v_usuario.datanascimento = v_data_objeto
                else:
                    setattr(v_usuario, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except (ValueError, TypeError) as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "Um ou mais campos possuem valores com tipo incorreto"}), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e)
          # Retorna erro caso o usuário tente atualizar o email para um que já existe no banco
          if 'Duplicate entry' in v_erro_str or 'UNIQUE constraint failed' in v_erro_str:
                return jsonify({"erro": "Conflito", "mensagem": "Email já em uso"}), 409
          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de tipo ou integridade nos dados"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Usuario/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_user(id):
      """
      Remove um usuário do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      try:
          v_usuario = db.session.get(Usuario, id)

          if not v_usuario:
              return jsonify({"erro": "Não encontrado"}), 404
            
          # Verifica se o usuário possui vínculo como colaborador para evitar exclusões errôneas
          v_vinc_colab = Colaborador.query.filter_by(idusuario=id).first()
        
          if v_vinc_colab:
            return jsonify({
                "erro": "Conflito de integridade", 
                "mensagem": "Não é possível remover este usuário pois ele possui um vínculo ativo como colaborador"
            }), 409
          
          db.session.delete(v_usuario)
          db.session.commit()
          return jsonify({"mensagem": "Removido"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/login', methods=['POST'])
  def f_login():
      """
      Autentica o usuário e inicia sessão
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            properties:
              email:
                type: string
                example: "joao@gmail.com"
              senha:
                type: string
                example: "senhainicial"
      responses:
        200:
          description:
        400:
          description:
        401:
          description:
        503:
          description:
      """
      v_dados = request.get_json(silent=True)
        
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "Credenciais não fornecidas em formato JSON"}), 400
      
      v_email = v_dados.get('email')
      v_senha = v_dados.get('senha')
        
      if not v_email or not v_senha:
          return jsonify({"mensagem": "Email e senha são obrigatórios"}), 400

      try:
          # Executa a busca utilizando a condição de filtro do SQLAlchemy (query.filter)
          v_user = Usuario.query.filter(Usuario.email == v_email).first()
          if v_user and v_user.f_verificar_senha(v_senha):
              login_user(v_user)
              return jsonify({"mensagem": "Logado com sucesso"}), 200
      except Exception:
          return jsonify({"erro": "Erro de serviço", "mensagem": "Indisponibilidade momentânea no sistema de login"}), 503
        
      return jsonify({"mensagem": "Credenciais inválidas"}), 401

  @v_app.route('/logout', methods=['POST'])
  @login_required
  def f_logout():
      """
      Encerra a sessão do usuário
      ---
      responses:
        200:
          description:
      """
      logout_user()
      return jsonify({"mensagem": "Sessão encerrada com sucesso"}), 200

  # ENDPOINTS DE LOG

  @v_app.route('/Usuario/log/add', methods=['POST'])
  def f_create_log():
      """
      Cadastra manualmente um novo log
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: Log
            required:
              - evento
            properties:
              idusuario:
                type: integer
                example: 1
              evento:
                type: string
                example: "Este é um novo evento."
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)

      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido ou malformado"}), 400
      
      v_campos_obrigatorios = ['evento']
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400

      v_id_user = v_dados.get('idusuario')
      if v_id_user is not None and not isinstance(v_id_user, int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'idusuario' deve ser um número inteiro"}), 400

      try: 
          v_novo_log = Log(
              idusuario=v_id_user,
              evento=v_dados.get('evento')
          )
          db.session.add(v_novo_log)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_novo_log.id}), 201
      except IntegrityError as e:
          db.session.rollback()
          return jsonify({
              "erro": "Erro de integridade",
              "mensagem": "O usuário informado não existe ou houve uma falha de vínculo no banco"
          }), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Usuario/log/<int:id>', methods=['GET'])
  @login_required
  def f_read_log(id):
      """
      Busca um log pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID único do log
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_log = db.session.get(Log, id)
          if not v_log:
              return jsonify({"erro": "Não encontrado"}), 404
          return jsonify(v_log.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # Este endpoint específico é polimórfico
  @v_app.route('/Usuario/log/all', methods=['GET'])
  @login_required
  def f_read_all_logs():
      """
      Busca todos os logs registrados, ou aplica filtros caso sejam enviados parâmetros de busca
      ---
      parameters:
        - name: evento
          in: query
          type: string
          description: Filtra por palavra que faça parte do evento
        - name: data_inicio
          in: query
          type: string
          description: Data inicial de um intervalo (DD/MM/YYYY)
        - name: data_fim
          in: query
          type: string
          description: Data final de um intervalo (DD/MM/YYYY)
        - name: hora_inicio
          in: query
          type: string
          description: Hora inicial de um intervalo (HH:MM:SS)
        - name: hora_fim
          in: query
          type: string
          description: Hora final de um intervalo (HH:MM:SS)
      responses:
        200:
          description:
        400:
          description:
        500:
          description:
      """
      v_dados = request.args.to_dict()
      v_resultados = []
                  
      try:
          v_query = Log.query
          v_agora = datetime.datetime.now()

          if v_dados:
              # Filtro de evento
              v_evento = v_dados.get('evento')
              if v_evento:
                  v_query = v_query.filter(Log.evento.like(f"%{v_evento}%"))

              # Filtros de data
              v_data_inicio_str = v_dados.get('data_inicio')

              if v_data_inicio_str:
                  v_data_inicio = f_validar_data(v_data_inicio_str)
                  if not v_data_inicio:
                      return jsonify({
                          "erro": "Formato inválido",
                          "mensagem": "data_inicio deve ser DD/MM/YYYY"
                      }), 400
                  
                  v_data_fim_str = v_dados.get('data_fim')
                  # Usa a data atual da requisição caso não haja data_fim
                  v_data_fim = f_validar_data(v_data_fim_str) if v_data_fim_str else v_agora.date()

                  v_query = v_query.filter(Log.data >= v_data_inicio, Log.data <= v_data_fim)

              # Filtros de hora
              v_hora_inicio_str = v_dados.get('hora_inicio')

              if v_hora_inicio_str:
                  v_hora_inicio = f_validar_hora(v_hora_inicio_str)
                  if not v_hora_inicio:
                      return jsonify({
                          "erro": "Formato inválido",
                          "mensagem": "hora_inicio deve ser HH:MM:SS"
                      }), 400

                  v_hora_fim_str = v_dados.get('hora_fim')
                  v_hora_fim = f_validar_hora(v_hora_fim_str) if v_hora_fim_str else v_agora.time()

                  v_query = v_query.filter(Log.hora >= v_hora_inicio, Log.hora <= v_hora_fim)
          v_resultados = v_query.all()
          return jsonify([v_r.f_para_dicionario() for v_r in v_resultados]), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
  
  # Gera log automaticamente quando alguma alteração ocorre
  @event.listens_for(db.session, 'after_flush')
  def f_gerar_log_automatico(v_session, v_flush_context):
      v_logs_para_adicionar = []

      try:
          v_autenticado = current_user.is_authenticated if current_user else False
          v_operador_nome = current_user.nome if v_autenticado else "Sistema/Anônimo"
          v_operador_id = current_user.id if v_autenticado else 0
      except Exception:
          v_operador_nome = "Sistema/Teste"
          v_operador_id = 0

      # Percorre objetos novos (new) e alterados (dirty)
      for v_obj in v_session.new.union(v_session.dirty):
          # Verifica se o modelo tem o atributo registralog e, caso sim, se é True
          if getattr(v_obj, 'registralog', False):
              v_label = getattr(v_obj, 'labellog', "Registro")
              v_nome_alvo = getattr(v_obj, 'nome', 'N/A')
              v_evento_str = ""

              # Para novos cadastros
              if v_obj in v_session.new:
                  v_evento_str = (
                      f"{v_label} cadastrado(a) | "
                      f"{v_label}: {v_nome_alvo} | "
                      f"ID do {v_label.lower()}: {v_obj.id} | "
                      f"Editado pelo usuário de ID {v_operador_id} e nome {v_operador_nome}"
                  )

              # Para edição de dados
              elif v_obj in v_session.dirty:
                  v_state = db.inspect(v_obj)
                    
                  # Verificação se houve mudança (não cria log caso nada tenha sido realmente alterado)
                  v_teve_mudanca = any(attr.history.has_changes() for attr in v_state.attrs)
                    
                  if v_teve_mudanca:
                      v_evento_str = (
                          f"{v_label} editado(a) | "
                          f"ID do {v_label.lower()}: {v_obj.id} ({v_nome_alvo}) | "
                          f"Editado pelo usuário de ID {v_operador_id} e nome {v_operador_nome}"
                      )

              if v_evento_str:
                  # O objeto Log é criado, mas ainda não recebe commit pois o flush está acontecendo
                  v_novo_log = Log(
                      idusuario=v_operador_id if v_operador_id > 0 else None,
                      evento=v_evento_str
                  )
                  v_logs_para_adicionar.append(v_novo_log)

      for v_l in v_logs_para_adicionar:
          v_session.add(v_l)

  # ENDPOINTS DE COLABORADOR
  
  @v_app.route('/Usuario/colaborador/add', methods=['POST'])
  @login_required
  def f_create_colaborador():
      """
      Cria um novo colaborador, vinculado a um usuário existente
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: Colaborador
            properties:
              idusuario:
                type: integer
                description: ID do usuário que será promovido à colaborador
                example: 1
      responses:
        201:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido ou malformado"}), 400

      v_idusuario = v_dados.get('idusuario')
      if v_idusuario is None:
          return jsonify({"erro": "Dados incompletos", "mensagem": "O campo 'idusuario' é obrigatório"}), 400
      
      if not isinstance(v_idusuario, int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'idusuario' deve ser um número inteiro"}), 400

      try:
          v_user_existe = db.session.get(Usuario, v_idusuario)
          if not v_user_existe:
              return jsonify({"erro": "Não encontrado", "mensagem": "O usuário informado não existe"}), 404

          if Colaborador.query.filter_by(idusuario=v_idusuario).first():
              return jsonify({"erro": "Conflito", "mensagem": "Este usuário já está vinculado como colaborador"}), 409

          v_novo_colaborador = Colaborador(idusuario=v_idusuario)
          db.session.add(v_novo_colaborador)
          db.session.commit()

          return jsonify(v_novo_colaborador.f_para_dicionario()), 201
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)
          if 'Duplicate entry' in v_erro_str or 'UNIQUE constraint failed' in v_erro_str:
              return jsonify({"erro": "Conflito", "mensagem": "Vínculo de colaborador já existe para este ID"}), 409
          return jsonify({"erro": "Erro de integridade", "mensagem": "Não foi possível criar o vínculo"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Usuario/colaborador/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_colaborador(id):
      """
      Busca um colaborador pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID do registro na tabela de colaboradores
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_colaborador = db.session.get(Colaborador, id)

          if not v_colaborador:
              return jsonify({"erro": "Não encontrado", "mensagem": "Colaborador não localizado no sistema"}), 404
          
          return jsonify(v_colaborador.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Falha ao conectar ao servidor para buscar o colaborador"
          }), 503

  @v_app.route('/Usuario/colaborador/get', methods=['GET'])
  @login_required
  def f_read_all_colaboradores():
      """
      Busca todos os colaboradores cadastrados
      ---
      responses:
        200:
          description:
        503:
          description:
      """
      try:
          v_lista = Colaborador.query.all()
          v_resultado = [v.f_para_dicionario() for v in v_lista]
          
          return jsonify(v_resultado), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível recuperar a lista de colaboradores"
          }), 503
      
  @v_app.route('/Usuario/colaborador/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_colaborador(id):
      """
      Atualiza dados de um colaborador existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
              idusuario:
                type: integer
                example: 1
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      v_colaborador = Colaborador.query.get_or_404(id)
      
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida"}), 400
      
      v_campos_permitidos = ['idusuario']

      try:
          for v_chave, v_valor in v_dados.items():
              if v_chave in v_campos_permitidos:
                  if v_chave == 'idusuario':
                      if not isinstance(v_valor, int):
                          raise TypeError("O campo idusuario deve ser um número inteiro")
                      v_colaborador.idusuario = v_valor
                  else:
                      setattr(v_colaborador, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify(v_colaborador.f_para_dicionario()), 200
      except TypeError as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except IntegrityError:
          db.session.rollback()
          return jsonify({"erro": "Conflito", "mensagem": "Este usuário já está vinculado a um colaborador"}), 409
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Usuario/colaborador/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_colaborador(id):
      """
      Remove um colaborador do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      try:
          v_colaborador = Colaborador.query.get_or_404(id)
          db.session.delete(v_colaborador)
          db.session.commit()
          return jsonify({"mensagem": "Colaborador removido com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE VÍNCULO COLABORADOR-DEPARTAMENTO

  @v_app.route('/Usuario/colaborador/departamento/add', methods=['POST'])
  @login_required
  def f_create_colaborador_departamento():
      """
      Cria um vínculo entre um colaborador e um departamento
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: ColaboradorDepartamento
            properties:
              idcolaborador:
                type: integer
              iddepartamento:
                type: integer
              scrum:
                type: integer
                default: 0
      responses:
        201:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        503:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_idcolaborador = v_dados.get('idcolaborador')
      v_iddepartamento = v_dados.get('iddepartamento')
      v_scrum = v_dados.get('scrum', 0)

      if not v_idcolaborador or not v_iddepartamento:
          return jsonify({"erro": "Dados incompletos", "mensagem": "ID do colaborador e ID do departamento são obrigatórios"}), 400
      
      if not isinstance(v_scrum, int):
          return jsonify({"erro": "Tipo inválido", "mensagem": "O campo 'scrum' deve ser um número inteiro"}), 400

      try:
          if not db.session.get(Colaborador, v_idcolaborador):
              return jsonify({"erro": "Não encontrado", "mensagem": "Colaborador não existe"}), 404

          if not db.session.get(Departamento, v_iddepartamento):
              return jsonify({"erro": "Não encontrado", "mensagem": "O departamento informado não existe"}), 404
          
          v_novo_vinculo = ColaboradorDepartamento(
              idcolaborador=v_idcolaborador,
              iddepartamento=v_iddepartamento,
              scrum=v_scrum
          )
          db.session.add(v_novo_vinculo)
          db.session.commit()
          return jsonify(v_novo_vinculo.f_para_dicionario()), 201
      except IntegrityError:
          db.session.rollback()
          return jsonify({"erro": "Conflito", "mensagem": "Este vínculo já existe ou viola integridade do banco"}), 409
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Usuario/colaborador/departamento/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_colaborador_departamento(id):
      """
      Busca um vínculo de colaborador-departamento pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID único do vínculo
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_vinculo = db.session.get(ColaboradorDepartamento, id)

          if not v_vinculo:
              return jsonify({"erro": "Não encontrado"}), 404
          
          return jsonify(v_vinculo.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível conectar ao servidor para buscar o vínculo"
          }), 503
  
  @v_app.route('/Usuario/colaborador/departamento/get', methods=['GET'])
  @login_required
  def f_read_all_colaborador_departamentos():
      """
      Busca todos os vínculos de colaborador-departamento cadastrados
      ---
      responses:
        200:
          description:
        503:
          description:
      """
      try:
          v_vinculos = ColaboradorDepartamento.query.all()
          v_lista_vinculos = [v.f_para_dicionario() for v in v_vinculos]
          
          return jsonify(v_lista_vinculos), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível recuperar a lista de vínculos"
          }), 503

  @v_app.route('/Usuario/colaborador/departamento/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_colaborador_departamento(id):
      """
      Atualiza os dados de um vínculo entre colaborador e departamento
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID do registro de vínculo
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
              idcolaborador:
                type: integer
              iddepartamento:
                type: integer
              scrum:
                type: integer
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      v_vinculo = db.session.get(ColaboradorDepartamento, id)
      if not v_vinculo:
          return jsonify({"erro": "Não encontrado"}), 404

      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida"}), 400

      v_campos_permitidos = ['idcolaborador', 'iddepartamento', 'scrum']

      try:
          for v_chave, v_valor in v_dados.items():
              if v_chave in v_campos_permitidos:
                  if v_chave in ['idcolaborador', 'iddepartamento', 'scrum'] and not isinstance(v_valor, int):
                      raise TypeError(f"O campo {v_chave} deve ser inteiro")
                  setattr(v_vinculo, v_chave, v_valor)

          db.session.commit()
          return jsonify(v_vinculo.f_para_dicionario()), 200
      except TypeError as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Usuario/colaborador/departamento/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_colaborador_departamento(id):
      """
      Remove o vínculo entre um colaborador e um departamento
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID do registro de vínculo a ser removido
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      v_vinculo = db.session.get(ColaboradorDepartamento, id)
      if not v_vinculo:
          return jsonify({"erro": "Não encontrado"}), 404

      try:
          db.session.delete(v_vinculo)
          db.session.commit()
          return jsonify({"mensagem": "Vínculo removido com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  # ENDPOINTS DE DEPARTAMENTO

  @v_app.route('/Departamento/add', methods=['POST'])
  @login_required
  def f_create_departamento():
      """
      Cria um novo departamento
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: Departamento
            properties:
              nome:
                type: string
                example: "Marketing"
      responses:
        201:
          description:
        400:
          description:
        503:
          description:
      """
      v_dados = request.get_json(silent=True)
      if not v_dados or 'nome' not in v_dados:
          return jsonify({"erro": "Dados inválidos", "mensagem": "O campo 'nome' é obrigatório"}), 400

      try:
          v_departamento = Departamento(nome=v_dados.get('nome'))
          db.session.add(v_departamento)
          db.session.commit()
          return jsonify(v_departamento.f_para_dicionario()), 201
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 503

  @v_app.route('/Departamento/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_departamento(id):
      """
      Busca um departamento pelo seu ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_dept = db.session.get(Departamento, id)
          if not v_dept:
              return jsonify({"erro": "Não encontrado", "mensagem": "Departamento inexistente"}), 404
          
          return jsonify(v_dept.f_para_dicionario()), 200
      except Exception:
          return jsonify({"erro": "Erro de banco", "mensagem": "Falha na conexão"}), 503

  @v_app.route('/Departamento/get', methods=['GET'])
  @login_required
  def f_read_all_departamentos():
      """
      Lista todos os departamentos
      ---
      responses:
        200:
          description:
        503:
          description:
      """
      try:
          v_lista = Departamento.query.all()
          return jsonify([d.f_para_dicionario() for d in v_lista]), 200
      except Exception:
          return jsonify({"erro": "Erro de banco", "mensagem": "Falha na conexão"}), 503

  @v_app.route('/Departamento/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_departamento(id):
      """
      Atualiza dados de um departamento
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
              nome:
                type: string
                example: "RH"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      v_dept = db.session.get(Departamento, id)
      if not v_dept:
          return jsonify({"erro": "Não encontrado"}), 404

      v_dados = request.get_json(silent=True)

      v_campos_permitidos = ['nome']

      try:
          for v_chave, v_valor in v_dados.items():
              if v_chave in v_campos_permitidos:
                  setattr(v_dept, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify(v_dept.f_para_dicionario()), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Departamento/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_departamento(id):
      """
      Remove um departamento
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      v_dept = db.session.get(Departamento, id)
      if not v_dept:
          return jsonify({"erro": "Não encontrado"}), 404

      try:
          db.session.delete(v_dept)
          db.session.commit()
          return jsonify({"mensagem": "Departamento removido com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
  
  # ENDPOINTS DE EMPRESA

  @v_app.route('/Empresa/add', methods=['POST'])
  @login_required
  def f_create_empresa():
      """
      Cadastra uma nova empresa
      ---
      parameters:
      - name: body
        in: body
        required: true
        schema:
          id: Empresa
          required:
            - cnpj
            - ie
            - telefone
            - email
            - rua
            - numero
            - bairro
            - cidade
            - uf
            - cep
            - mapa
            - valorcontrato
            - valordeslocamento
            - nvisitasfisicas
            - vigenciacontrato
            - diavencimento
          properties:
            razao:
              type: string
              example: "Minha Empresa Ltda."
            cnpj:
              type: string
              example: "00.000.000/0001-00"
            ie:
              type: string
              example: "123456789"
            telefone:
              type: string
              example: "40028922"
            email:
              type: string
              example: "contatoempresa@gmail.com"
            rua:
              type: string
              example: "Av. Paulista"
            numero:
              type: integer
              example: 1000
            bairro:
              type: string
              example: "Bela Vista"
            cidade:
              type: string
              example: "São Paulo"
            uf:
              type: string
              example: "SP"
            cep:
              type: string
              example: "01310-100"
            mapa:
              type: string
              example: "https://www.google.com/maps/place/lugar+ficticio"
            idusuario:
              type: integer
              example: 1
            valorcontrato:
              type: number
              format: float
              example: 1500.50
            valordeslocamento:
              type: number
              format: float
              example: 50.00
            nvisitasfisicas:
              type: integer
              example: 2
            vigenciacontrato:
              type: string
              example: "31/12/2026"
            diavencimento:
              type: integer
              example: 10
            estado:
              type: boolean
              example: true
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_campos_obrigatorios = [
          'cnpj', 'ie', 'telefone', 'email', 'rua', 'numero', 'bairro', 
          'cidade', 'uf', 'cep', 'mapa', 'valorcontrato', 
          'valordeslocamento', 'nvisitasfisicas', 'vigenciacontrato', 'diavencimento'
      ]
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400

      v_vigencia_str = v_dados.get('vigenciacontrato')
      if v_vigencia_str:
          v_data_objeto = f_validar_data(v_vigencia_str)
          if not v_data_objeto:
              return jsonify({"erro": "Formato inválido", "mensagem": "vigenciacontrato deve ser DD/MM/YYYY"}), 400
          v_dados['vigenciacontrato'] = v_data_objeto

      v_nova_empresa = Empresa(**v_dados)
      
      try:
          db.session.add(v_nova_empresa)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_nova_empresa.id}), 201
      except IntegrityError as e:
        db.session.rollback()
        v_erro_str = str(e.orig)
        
        if 'Duplicate entry' in v_erro_str or 'UNIQUE constraint failed' in v_erro_str:
            if 'cnpj' in v_erro_str:
                v_msg = f"O CNPJ '{v_dados.get('cnpj')}' já está cadastrado"
            elif 'email' in v_erro_str:
                v_msg = f"O email '{v_dados.get('email')}' já está cadastrado"
            else:
                v_msg = "Já existe um registro com estes dados únicos"
                
            return jsonify({
                "erro": "Conflito de dados",
                "mensagem": v_msg
            }), 409
            
        # Caso haja erro de chave estrangeira (isto é, se o idusuario não existir)
        return jsonify({"erro": "Erro de integridade", "detalhes": v_erro_str}), 400
      except (TypeError, ValueError) as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_empresa(id):
      """
      Busca uma empresa pelo ID
      ---
      parameters:
      - name: id
        in: path
        type: integer
        required: true
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_empresa = db.session.get(Empresa, id)
          if not v_empresa:
              return jsonify({"erro": "Não encontrado"}), 404
          return jsonify(v_empresa.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 503

  @v_app.route('/Empresa/get', methods=['GET'])
  @login_required
  def f_read_all_empresas():
      """
      Busca todas as empresas cadastradas
      ---
      responses:
        200:
          description:
        503:
          description:
      """
      try:
          v_empresas = Empresa.query.all()
          return jsonify([emp.f_para_dicionario() for emp in v_empresas]), 200
      except Exception as e:
          return jsonify({"erro": "Erro de banco de dados", "mensagem": "Não foi possível recuperar a lista"}), 503

  @v_app.route('/Empresa/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_empresa(id):
      """
      Atualiza dados de uma empresa existente
      ---
      parameters:
      - name: id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          properties:
            razao:
              type: string
              example: "Minha Outra Empresa Ltda."
            cnpj:
              type: string
              example: "00.000.000/0002-00"
            ie:
              type: string
              example: "987654321"
            telefone:
              type: string
              example: "89224002"
            email:
              type: string
              example: "novocontatoempresa@gmail.com"
            rua:
              type: string
              example: "Rua dos Bobos"
            numero:
              type: integer
              example: 500
            bairro:
              type: string
              example: "Bairro Qualquer"
            cidade:
              type: string
              example: "Belo Horizonte"
            uf:
              type: string
              example: "MG"
            cep:
              type: string
              example: "02420-200"
            mapa:
              type: string
              example: "https://www.google.com/maps/place/outro+lugar+ficticio"
            idusuario:
              type: integer
              example: 2
            valorcontrato:
              type: number
              format: float
              example: 750.25
            valordeslocamento:
              type: number
              format: float
              example: 100.00
            nvisitasfisicas:
              type: integer
              example: 3
            vigenciacontrato:
              type: string
              example: "31/12/2027"
            diavencimento:
              type: integer
              example: 20
            estado:
              type: boolean
              example: false
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      v_empresa = db.session.get(Empresa, id)
      if not v_empresa:
          return jsonify({"erro": "Não encontrado"}), 404
      
      v_novos_dados = request.get_json(silent=True)
      if v_novos_dados is None:
          return jsonify({"erro": "Requisição inválida"}), 400
      
      v_campos_permitidos = [
        'razao', 'cnpj', 'ie', 'telefone', 'email', 'rua', 'numero', 
        'bairro', 'cidade', 'uf', 'cep', 'mapa', 'idusuario', 
        'valorcontrato', 'valordeslocamento', 'nvisitasfisicas', 
        'vigenciacontrato', 'diavencimento', 'estado'
      ]

      try:
        for v_chave, v_valor in v_novos_dados.items():
            if v_chave in v_campos_permitidos:
                if v_chave in ['numero', 'nvisitasfisicas', 'diavencimento'] and v_valor is not None:
                    if not isinstance(v_valor, int):
                        raise TypeError(f"O campo {v_chave} deve ser um número inteiro")

                if v_chave == 'vigenciacontrato' and v_valor:
                    v_data_objeto = f_validar_data(v_valor)
                    if not v_data_objeto:
                        return jsonify({"erro": "Data inválida", "mensagem": "Use DD/MM/YYYY"}), 400
                    v_empresa.vigenciacontrato = v_data_objeto
                else:
                    setattr(v_empresa, v_chave, v_valor)

        db.session.flush()
        db.session.commit()
        return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except (ValueError, TypeError) as e:
          db.session.rollback()
          return jsonify({
              "erro": "Tipo de dado inválido", 
              "mensagem": str(e) if str(e) else "Um ou mais campos possuem valores com tipo incorreto"
          }), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)
          if 'Duplicate entry' in v_erro_str or 'UNIQUE constraint failed' in v_erro_str:
              return jsonify({"erro": "Conflito", "mensagem": "CNPJ ou email já em uso"}), 409
          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de integridade nos dados"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_empresa(id):
      """
      Remove uma empresa do sistema
      ---
      parameters:
      - name: id
        in: path
        type: integer
        required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_empresa = db.session.get(Empresa, id)
          if not v_empresa:
              return jsonify({"erro": "Não encontrado"}), 404
          
          db.session.delete(v_empresa)
          db.session.commit()
          return jsonify({"mensagem": "Removido"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE ACESSO EXTERNO

  @v_app.route('/Empresa/AcessoExterno/add', methods=['POST'])
  @login_required
  def f_create_acesso_externo():
      """
      Cadastra um novo acesso externo para uma empresa
      ---
      parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - id_empresa
            - descricao
            - ip
            - peso
          properties:
            id_empresa:
              type: integer
              example: 1
            descricao:
              type: string
              example: "Servidor de backup"
            ip:
              type: string
              example: "192.168.1.100"
            peso:
              type: integer
              example: 5
            sentinela:
              type: integer
              example: 1
            porta:
              type: string
              example: "1319"
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_campos_obrigatorios = ['id_empresa', 'descricao', 'ip', 'peso']
      
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400

      try:
          if not isinstance(v_dados.get('id_empresa'), int):
              raise TypeError("O campo id_empresa deve ser um número inteiro")
          
          if not isinstance(v_dados.get('peso'), int):
              raise TypeError("O campo peso deve ser um número inteiro")
          
          if 'sentinela' in v_dados and not isinstance(v_dados.get('sentinela'), int):
              raise TypeError("O campo sentinela deve ser um número inteiro (0 ou 1)")
      except TypeError as e:
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400

      v_novo_acesso = AcessoExterno(**v_dados)
      
      try:
          db.session.add(v_novo_acesso)
          db.session.commit()
          
          return jsonify({
              "mensagem": "Acesso externo cadastrado com sucesso", 
              "id": v_novo_acesso.id
          }), 201
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig).lower()
          
          if 'foreign key' in v_erro_str:
            return jsonify({
                "erro": "Conflito de integridade", 
                "mensagem": f"A empresa com ID {v_dados.get('id_empresa')} não existe"
            }), 409
              
          return jsonify({"erro": "Erro de integridade", "detalhes": v_erro_str}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/AcessoExterno/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_acesso_externo(id):
      """
      Retorna um acesso externo específico através do seu ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_acesso = AcessoExterno.query.get_or_404(id)
      return jsonify(v_acesso.f_para_dicionario()), 200

  @v_app.route('/Empresa/AcessoExterno/get', methods=['GET'])
  @login_required
  def f_read_all_acessos_externos():
      """
      Retorna a lista de todos os acessos externos cadastrados
      ---
      responses:
        200:
          description:
        401:
          description:
        500:
          description:
      """
      v_acessos = AcessoExterno.query.all()
      return jsonify([v.f_para_dicionario() for v in v_acessos]), 200

  @v_app.route('/Empresa/AcessoExterno/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_acesso_externo(id):
      """
      Atualiza dados de um acesso externo existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
              id_empresa:
                type: integer
                example: 2
              descricao:
                type: string
                example: "Servidor de produção"
              ip:
                type: string
                example: "10.0.0.50"
              peso:
                type: integer
                example: 10
              sentinela:
                type: integer
                example: 0
              porta:
                type: string
                example: "8080"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_acesso = AcessoExterno.query.get_or_404(id)

      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_campos_permitidos = ['id_empresa', 'descricao', 'ip', 'peso', 'sentinela', 'porta']

      try:
          for v_chave, v_valor in v_dados.items():
              if v_chave in v_campos_permitidos:
                  if v_chave in ['id_empresa', 'peso', 'sentinela']:
                      if v_valor is not None and not isinstance(v_valor, int):
                          raise TypeError(f"O campo {v_chave} deve ser um número inteiro")
                  
                  setattr(v_acesso, v_chave, v_valor)

          db.session.flush() 
          db.session.commit()

          return jsonify({"mensagem": "Sucesso", "id": v_acesso.id}), 200
      except TypeError as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig).lower()
          
          if 'foreign key' in v_erro_str:
              return jsonify({
                  "erro": "Conflito de integridade", 
                  "mensagem": f"A empresa informada não existe"
              }), 409
              
          return jsonify({"erro": "Erro de integridade", "detalhes": v_erro_str}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/AcessoExterno/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_acesso_externo(id):
      """
      Remove um acesso externo do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      v_acesso = AcessoExterno.query.get_or_404(id)

      try:
          db.session.delete(v_acesso)
          db.session.commit()
          
          return jsonify({"mensagem": "Sucesso", "id": id}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE LANÇAMENTO FINANCEIRO

  @v_app.route('/Financeiro/add', methods=['POST'])
  @login_required
  def f_create_financeiro():
      """
      Cadastra um novo lançamento financeiro (entrada/saída)
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            type: object
            required:
              - tipo
              - descricao
              - data
              - valor
              - centrocusto
            properties:
              tipo:
                type: string
                example: "Saída"
              descricao:
                type: string
                example: "Pagamento do fornecedor de peças"
              data:
                type: string
                example: "2026-04-06"
              valor:
                type: number
                example: 450.50
              os:
                type: integer
                example: 1022
              situacao:
                type: integer
                example: 1
              df:
                type: integer
                example: 0
              centrocusto:
                type: integer
                example: 5
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_campos_obrigatorios = ['tipo', 'descricao', 'data', 'valor', 'centrocusto']
      v_invalidos = [c for c in v_campos_obrigatorios if c not in v_dados or v_dados.get(c) is None]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400

      try:
          v_data_objeto = f_validar_data(v_dados.get('data'))

          if not v_data_objeto:
              return jsonify({"erro": "Formato inválido", "mensagem": "data deve ser DD/MM/YYYY"}), 400

          if not isinstance(v_dados['valor'], (int, float)):
              raise TypeError("O campo valor deve ser numérico")
          
          if not isinstance(v_dados['centrocusto'], int):
              raise TypeError("O campo centrocusto deve ser um número inteiro")

          v_centrocusto_existe = db.session.get(CentroCusto, v_dados['centrocusto'])
          if not v_centrocusto_existe:
            return jsonify({
                "erro": "Centro de custo inexistente", 
                "mensagem": f"O centro de custo com ID {v_dados['centrocusto']} não foi encontrado"
            }), 400
          
          v_novo_lancamento = Financeiro(
              tipo=v_dados.get('tipo'),
              descricao=v_dados.get('descricao'),
              data=v_data_objeto,
              valor=float(v_dados.get('valor')),
              os=v_dados.get('os'),
              idusuario=current_user.id,
              situacao=v_dados.get('situacao', 1), # Padrão é "sim" se a informação não for enviada
              df=v_dados.get('df', 0),
              centrocusto=v_dados.get('centrocusto')
          )

          db.session.add(v_novo_lancamento)
          db.session.commit()

          return jsonify({
              "mensagem": "Sucesso",
              "id": v_novo_lancamento.id
          }), 201
      except TypeError as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
  
  @v_app.route('/Financeiro/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_financeiro(id):
      """
      Retorna um lançamento financeiro específico pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_lancamento = Financeiro.query.get_or_404(id)
      return jsonify(v_lancamento.f_para_dicionario()), 200

  @v_app.route('/Financeiro/get', methods=['GET'])
  @login_required
  def f_read_all_financeiros():
      """
      Retorna a lista completa de lançamentos financeiros
      ---
      responses:
        200:
          description:
        500:
          description:
      """
      try:
          v_lancamentos = Financeiro.query.all()
          return jsonify([v.f_para_dicionario() for v in v_lancamentos]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Financeiro/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_financeiro(id):
      """
      Atualiza um lançamento financeiro existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            type: object
            properties:
              tipo:
                type: string
                example: "Entrada"
              descricao:
                type: string
                example: "Recebimento de mensalidade"
              data:
                type: string
                example: "2026-04-10"
              valor:
                type: number
                example: 1200.00
              os:
                type: integer
                example: 1023
              situacao:
                type: integer
                example: 2
              df:
                type: integer
                example: 1
              centrocusto:
                type: integer
                example: 4
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      v_lancamento = Financeiro.query.get_or_404(id)
      v_dados = request.get_json(silent=True)

      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_campos_permitidos = ['tipo', 'descricao', 'data', 'valor', 'os', 'situacao', 'df', 'centrocusto']

      try:
          for v_chave, v_valor in v_dados.items():
              if v_chave in v_campos_permitidos:
                  if v_chave == 'data' and v_valor:
                    v_data_objeto = f_validar_data(v_valor)
                    if not v_data_objeto:
                        return jsonify({"erro": "Data inválida", "mensagem": "Use DD/MM/YYYY"}), 400
                    v_valor = v_data_objeto

                  if v_chave in ['valor'] and not isinstance(v_valor, (int, float)):
                      raise TypeError(f"O campo {v_chave} deve ser um número")
                  
                  if v_chave in ['situacao', 'df', 'centrocusto', 'os'] and v_valor is not None:
                      if not isinstance(v_valor, int):
                          raise TypeError(f"O campo {v_chave} deve ser um número inteiro")

                  if v_chave == 'centrocusto':
                    v_centrocusto_existe = db.session.get(CentroCusto, v_valor)
                    if not v_centrocusto_existe:
                        return jsonify({
                            "erro": "Centro de custo inexistente", 
                            "mensagem": f"O centro de custo com ID {v_valor} não foi encontrado"
                        }), 400

                  setattr(v_lancamento, v_chave, v_valor)

          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_lancamento.id}), 200
      except TypeError as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Financeiro/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_financeiro(id):
      """
      Remove um lançamento financeiro do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      v_lancamento = Financeiro.query.get_or_404(id)

      try:
          db.session.delete(v_lancamento)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": id}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE MENU

  @v_app.route('/Menu/add', methods=['POST'])
  @login_required
  def f_create_menu():
      """
      Cadastra um novo item de menu
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: Menu
            required:
              - posicao
              - texto
              - url
            properties:
              posicao:
                type: integer
                example: 1
              texto:
                type: string
                example: "Página inicial"
              url:
                type: string
                example: "/home"
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_campos_obrigatorios = ['posicao', 'texto', 'url']
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400

      if not isinstance(v_dados.get('posicao'), int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'posicao' deve ser um número inteiro"}), 400

      v_novo_item = Menu(**v_dados)
      
      try:
          db.session.add(v_novo_item)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "posicao": v_novo_item.posicao}), 201
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)

          if 'Duplicate entry' in v_erro_str or 'PRIMARY' in v_erro_str:
              return jsonify({
                  "erro": "Conflito de dados",
                  "mensagem": f"A posição '{v_dados.get('posicao')}' já está ocupada por outro item de menu"
              }), 409
          
          return jsonify({"erro": "Erro de integridade", "detalhes": v_erro_str}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Menu/get/<int:posicao>', methods=['GET'])
  @login_required
  def f_read_menu(posicao):
      """
      Busca um item de menu pela posição
      ---
      parameters:
        - name: posicao
          in: path
          type: integer
          required: true
          description: Posição única do item
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      v_menu = Menu.query.get(posicao)
      if not v_menu:
          return jsonify({"erro": "Não encontrado", "mensagem": "Menu não localizado"}), 404
      
      return jsonify(v_menu.f_para_dicionario()), 200

  @v_app.route('/Menu/get', methods=['GET'])
  @login_required
  def f_read_all_menus():
      """
      Lista todos os itens de menu cadastrados
      ---
      responses:
        200:
          description:
        500:
          description:
        503:
          description:
      """
      try:
          v_menus = Menu.query.order_by(Menu.posicao).all()
          v_lista = [m.f_para_dicionario() for m in v_menus]

          return jsonify(v_lista), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Menu/upd/<int:posicao>', methods=['PUT'])
  @login_required
  def f_update_menu(posicao):
      """
      Atualiza dados de um item de menu existente
      ---
      parameters:
        - name: posicao
          in: path
          type: integer
          required: true
          description: Posição do item a ser editado
        - name: body
          in: body
          required: true
          schema:
            properties:
              texto:
                type: string
                example: "Relatórios"
              url:
                type: string
                example: "/relatorios"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      v_menu = db.session.get(Menu, posicao)

      if not v_menu:
          return jsonify({"erro": "Não encontrado", "mensagem": "Menu não localizado"}), 404
      
      v_novos_dados = request.get_json(silent=True)
      if v_novos_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400
      
      v_campos_permitidos = ['texto', 'url']

      try:
          for v_chave, v_valor in v_novos_dados.items():
              if v_chave in v_campos_permitidos:
                  setattr(v_menu, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso", "posicao": v_menu.posicao}), 200
      except (ValueError, TypeError) as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Menu/del/<int:posicao>', methods=['DELETE'])
  @login_required
  def f_delete_menu(posicao):
      """
      Remove um item de menu do sistema
      ---
      parameters:
        - name: posicao
          in: path
          type: integer
          required: true
          description: Posição única do item a ser excluído
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      v_menu = db.session.get(Menu, posicao)

      if not v_menu:
          return jsonify({"erro": "Não encontrado", "mensagem": "Menu não localizado"}), 404

      try:
          db.session.delete(v_menu)
          db.session.commit()
          return jsonify({"mensagem": "Removido com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  # ENDPOINTS DE PÁGINA

  @v_app.route('/Pagina/add', methods=['POST'])
  @login_required
  def f_create_pagina():
      """
      Cadastra uma nova página
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: Pagina
            required:
              - url
              - title
              - banner
              - description
            properties:
              url:
                type: string
                example: "servicos/manutencao"
              title:
                type: string
                example: "Manutenção de equipamentos"
              banner:
                type: string
                example: "banner_manutencao.jpg"
              description:
                type: string
                example: "Descrição da página de manutenção"
              conteudo:
                type: string
                example: "Conteúdo detalhado aqui"
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido ou malformado"}), 400

      v_campos_obrigatorios = ['url', 'title', 'banner', 'description']
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or not v_dados.get(campo)]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400

      v_url_existente = Pagina.query.filter_by(url=v_dados.get('url')).first()
      if v_url_existente:
          return jsonify({
              "erro": "Conflito de dados",
              "mensagem": f"A URL '{v_dados.get('url')}' já está em uso"
          }), 409

      v_nova_pagina = Pagina(**v_dados)

      try:
          db.session.add(v_nova_pagina)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_nova_pagina.id}), 201
      except IntegrityError as e:
          db.session.rollback()
          return jsonify({"erro": "Erro de integridade", "mensagem": "Erro ao salvar no banco de dados"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Pagina/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_pagina(id):
      """
      Busca uma página pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_pagina = db.session.get(Pagina, id)

          if not v_pagina:
              return jsonify({"erro": "Não encontrado", "mensagem": "Página não localizada no sistema"}), 404
          
          return jsonify(v_pagina.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro de banco de dados", "mensagem": "Não foi possível conectar ao servidor"}), 503

  @v_app.route('/Pagina/url/get', methods=['GET'])
  @login_required
  def f_read_pagina_by_url():
      """
      Busca uma página pela sua URL
      ---
      parameters:
        - name: url
          in: query
          type: string
          required: true
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_url_param = request.args.get('url')
          
          if not v_url_param:
              return jsonify({"erro": "Requisição inválida", "mensagem": "O parâmetro 'url' é obrigatório"}), 400

          v_pagina = Pagina.query.filter_by(url=v_url_param).first()

          if not v_pagina:
              return jsonify({"erro": "Não encontrado", "mensagem": f"Nenhuma página com a URL '{v_url_param}'"}), 404
          
          return jsonify(v_pagina.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro de banco de dados", "mensagem": str(e)}), 503
      
  @v_app.route('/Pagina/get', methods=['GET'])
  @login_required
  def f_read_all_paginas():
      """
      Busca todas as páginas cadastradas
      ---
      responses:
        200:
          description:
        503:
          description:
      """
      try:
          v_paginas = Pagina.query.all()
          v_lista = [v_p.f_para_dicionario() for v_p in v_paginas]
          
          return jsonify(v_lista), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível recuperar a lista de páginas"
          }), 503
      
  @v_app.route('/Pagina/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_pagina(id):
      """
      Atualiza dados de uma página existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              url:
                type: string
                example: "quem-somos"
              title:
                type: string
                example: "Sobre nós"
              banner:
                type: string
                example: "banner_sobre.jpg"
              description:
                type: string
                example: "Nossa história e valores"
              conteudo:
                type: string
                example: "Conteúdo da página"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_pagina = db.session.get(Pagina, id)

      if not v_pagina:
          return jsonify({"erro": "Não encontrado", "mensagem": "Página não localizada"}), 404
      
      v_novos_dados = request.get_json(silent=True)
      if v_novos_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON malformado"}), 400
      
      v_campos_permitidos = ['url', 'title', 'banner', 'description', 'conteudo']

      try:
          for v_chave, v_valor in v_novos_dados.items():
              if v_chave in v_campos_permitidos:
                  setattr(v_pagina, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)

          if 'Duplicate entry' in v_erro_str or 'UNIQUE constraint failed' in v_erro_str:
              return jsonify({"erro": "Conflito", "mensagem": "Esta URL já está sendo utilizada"}), 409
          
          return jsonify({"erro": "Erro de integridade", "mensagem": "Dados incompatíveis"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Pagina/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_pagina(id):
      """
      Remove uma página do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_pagina = db.session.get(Pagina, id)

          if not v_pagina:
              return jsonify({"erro": "Não encontrado", "mensagem": "Página não localizada"}), 404
          
          db.session.delete(v_pagina)
          db.session.commit()
          return jsonify({"mensagem": "Removido com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE VÍNCULO COLABORADOR-EMPRESA

  @v_app.route('/Empresa/<int:idempresa>/Colaborador/add', methods=['POST'])
  @login_required
  def f_create_colaborador_empresa(idempresa):
      """
      Cadastra um novo colaborador vinculado a uma empresa específica
      ---
      parameters:
        - name: idempresa
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            id: ColaboradorEmpresa
            required:
              - nome
              - nick
              - email
              - senha
              - estado
            properties:
              nome:
                type: string
                example: "Carlos Andrade"
              nick:
                type: string
                example: "carlos.ti"
              email:
                type: string
                example: "carlosparceiro@gmail.com"
              senha:
                type: string
                example: "senha123"
              estado:
                type: integer
                description: 0 para desabilitado, 1 para habilitado
                example: 1
              telefone:
                type: string
                example: "(11) 99999-9999"
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if not v_dados:
          return jsonify({"erro": "JSON não fornecido"}), 400

      v_empresa = db.session.get(Empresa, idempresa)
      if not v_empresa:
          return jsonify({"erro": "Empresa inexistente"}), 400
      
      if not v_empresa.estado:
          return jsonify({
              "erro": "Empresa inativa", 
              "mensagem": f"A empresa {v_empresa.razao} não está habilitada para o uso"
          }), 400

      v_campos = ['nome', 'nick', 'email', 'senha', 'estado']
      for v_campo in v_campos:
          if v_campo not in v_dados or v_dados.get(v_campo) is None:
              return jsonify({"erro": "Dados incompletos", "mensagem": f"O campo {v_campo} é obrigatório"}), 400

      if v_dados['estado'] not in [0, 1]:
          return jsonify({"erro": "Estado inválido", "mensagem": "Use 0 para desabilitado ou 1 para habilitado"}), 400

      v_telefone_limpo = None
      if 'telefone' in v_dados and v_dados['telefone']:
          # Remove as máscaras do telefone fornecido
          v_telefone_limpo = re.sub(r'\D', '', str(v_dados['telefone']))
          
          # Validação de telefone duplicado
          v_existente = ColaboradorEmpresa.query.filter_by(telefone=v_telefone_limpo).first()
          if v_existente:
              v_empresa_dona = db.session.get(Empresa, v_existente.idempresa)
              return jsonify({
                  "erro": "Telefone já cadastrado",
                  "mensagem": f"Estes dados já existem na empresa de ID {v_empresa_dona.id} e razão {v_empresa_dona.razao}"
              }), 409

      # Validação de email duplicado
      v_email_existe = ColaboradorEmpresa.query.filter_by(email=v_dados['email']).first()
      if v_email_existe:
          return jsonify({"erro": "Email em uso", "mensagem": "Este email já está cadastrado no sistema"}), 409

      try:
          v_senha_pura = v_dados.pop('senha')
          v_novo_colab = ColaboradorEmpresa(
              idempresa=idempresa,
              nome=v_dados['nome'],
              nick=v_dados['nick'],
              email=v_dados['email'],
              estado=v_dados['estado'],
              telefone=v_telefone_limpo
          )
          v_novo_colab.f_definir_senha(v_senha_pura)

          db.session.add(v_novo_colab)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_novo_colab.id}), 201
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/<int:idempresa>/Colaborador/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_colaborador_empresa(idempresa, id):
      """
      Busca um colaborador específico de uma empresa
      ---
      parameters:
        - name: idempresa
          in: path
          type: integer
          required: true
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      # Garante que o ID do colaborador esteja vinculado ao ID da empresa em questão
      v_colaborador = ColaboradorEmpresa.query.filter_by(id=id, idempresa=idempresa).first()

      if not v_colaborador:
          return jsonify({
              "erro": "Não encontrado", 
              "mensagem": "Colaborador não existe ou não pertence a esta empresa"
          }), 404

      return jsonify(v_colaborador.f_para_dicionario()), 200
  
  @v_app.route('/Empresa/<int:idempresa>/Colaborador/get', methods=['GET'])
  @login_required
  def f_read_all_colaboradores_empresa(idempresa):
      """
      Lista todos os colaboradores vinculados a uma empresa específica
      ---
      parameters:
        - name: idempresa
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_empresa = db.session.get(Empresa, idempresa)
      if not v_empresa:
          return jsonify({"erro": "Empresa não encontrada"}), 404

      # Busca apenas os colaboradores de uma determinada empresa
      v_colaboradores = ColaboradorEmpresa.query.filter_by(idempresa=idempresa).all()
      
      return jsonify([v_c.f_para_dicionario() for v_c in v_colaboradores]), 200

  @v_app.route('/Empresa/<int:idempresa>/Colaborador/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_colaborador_empresa(idempresa, id):
      """
      Atualiza os dados do colaborador de uma empresa
      ---
      parameters:
        - name: idempresa
          in: path
          type: integer
          required: true
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              nome:
                type: string
                example: "Carlos Editado"
              nick:
                type: string
                example: "carlos.edit"
              email:
                type: string
                example: "carloseditado@gmail.com"
              estado:
                type: integer
                example: 0
              telefone:
                type: string
                example: "(12) 04002-8922"
              senha:
                type: string
                example: "password123"
      responses:
        200:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if not v_dados:
          return jsonify({"erro": "Requisição inválida"}), 400
      
      v_colaborador = ColaboradorEmpresa.query.filter_by(id=id, idempresa=idempresa).first()

      if not v_colaborador:
          return jsonify({"erro": "Não encontrado", "mensagem": "Colaborador não pertence a esta empresa"}), 404
      
      # Remove id e idempresa do JSON, caso tenham sido inseridos pelo usuário, para evitar alterações
      v_dados.pop('id', None)
      v_dados.pop('idempresa', None)

      if 'email' in v_dados and v_dados['email'] != v_colaborador.email:
          v_email_existe = ColaboradorEmpresa.query.filter_by(email=v_dados['email']).first()
          if v_email_existe:
              return jsonify({"erro": "Email em uso", "mensagem": "Este email já está cadastrado no sistema"}), 409

      if 'telefone' in v_dados and v_dados['telefone']:
          v_tel_limpo = re.sub(r'\D', '', str(v_dados['telefone']))
          # Busca se o telefone existe em qualquer outro registro que não seja o atual
          v_tel_existe = ColaboradorEmpresa.query.filter(
              ColaboradorEmpresa.telefone == v_tel_limpo, 
              ColaboradorEmpresa.id != id
          ).first()
          
          if v_tel_existe:
              v_emp_dona = db.session.get(Empresa, v_tel_existe.idempresa)
              return jsonify({
                  "erro": "Telefone já cadastrado",
                  "mensagem": f"Estes dados já existem na empresa de ID {v_emp_dona.id} e razão {v_emp_dona.razao}"
              }), 409
          v_colaborador.telefone = v_tel_limpo

      if 'nome' in v_dados: v_colaborador.nome = v_dados['nome']
      if 'nick' in v_dados: v_colaborador.nick = v_dados['nick']
      if 'email' in v_dados: v_colaborador.email = v_dados['email']
      
      if 'estado' in v_dados:
          if v_dados['estado'] in [0, 1]:
              v_colaborador.estado = v_dados['estado']
          else:
              return jsonify({"erro": "Estado inválido"}), 400

      if 'senha' in v_dados and v_dados['senha']:
          v_colaborador.f_definir_senha(v_dados['senha'])

      try:
          db.session.commit()
          return jsonify({"mensagem": "Dados atualizados com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
    
  @v_app.route('/Empresa/<int:idempresa>/Colaborador/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_colaborador_empresa(idempresa, id):
      """
      Remove um colaborador de uma empresa
      ---
      parameters:
        - name: idempresa
          in: path
          type: integer
          required: true
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_colaborador = ColaboradorEmpresa.query.filter_by(id=id, idempresa=idempresa).first()

      if not v_colaborador:
          return jsonify({"erro": "Erro", "mensagem": "Registro não encontrado nesta empresa"}), 404

      v_vinc_acesso = ColaboradorAcesso.query.filter_by(idcolaboradoremail=id).first()

      if v_vinc_acesso:
          return jsonify({
              "erro": "Conflito de integridade",
              "mensagem": "Não é possível remover este colaborador pois existem registros de acesso vinculados a ele"
          }), 409

      try:
          db.session.delete(v_colaborador)
          db.session.commit()
          return jsonify({"mensagem": "Colaborador removido com sucesso"}), 200
      except IntegrityError as e:
          db.session.rollback()
          return jsonify({
              "erro": "Erro de integridade", 
              "mensagem": "Existem dependências que impedem a exclusão deste registro"
          }), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
    
  # ENDPOINTS DE CLIENTE

  @v_app.route('/Empresa/Api/add', methods=['POST'])
  @login_required
  def f_create_api_cliente():
      """
      Cadastra uma nova credencial de API para um cliente
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: ApiCliente
            required:
              - idcliente
              - idsentinela
              - usr
              - senha
            properties:
              idcliente:
                type: integer
                example: 1
              idsentinela:
                type: integer
                example: 10
              usr:
                type: string
                example: "api_user_tech"
              senha:
                type: string
                example: "senhasegura123"
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if not v_dados:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_campos = ['idcliente', 'idsentinela', 'usr', 'senha']
      v_faltantes = [c for c in v_campos if c not in v_dados or v_dados.get(c) is None]
      if v_faltantes:
          return jsonify({
              "erro": "Dados incompletos",
              "mensagem": f"Os campos {', '.join(v_faltantes)} são obrigatórios"
          }), 400

      v_usr_existe = ApiCliente.query.filter_by(usr=v_dados['usr']).first()
      if v_usr_existe:
          return jsonify({
              "erro": "Usuário já existe",
              "mensagem": f"O usuário '{v_dados['usr']}' já está cadastrado no sistema"
          }), 409

      v_empresa = db.session.get(Empresa, v_dados['idcliente'])
      if not v_empresa:
          return jsonify({
              "erro": "Cliente não encontrado",
              "mensagem": f"A empresa de ID {v_dados['idcliente']} não existe"
          }), 400

      v_sentinela = db.session.get(AcessoExterno, v_dados['idsentinela'])
      if not v_sentinela:
          return jsonify({
              "erro": "Sentinela não encontrado",
              "mensagem": f"O acesso externo de ID {v_dados['idsentinela']} não existe"
          }), 400
      
      if v_sentinela.id_empresa != v_dados['idcliente']:
          return jsonify({
              "erro": "Conflito de vínculo",
              "mensagem": "O sentinela informado não pertence à empresa selecionada"
          }), 400

      try:
          v_senha_pura = v_dados.pop('senha')
          v_nova_api = ApiCliente(**v_dados)
          v_nova_api.f_definir_senha(v_senha_pura)

          db.session.add(v_nova_api)
          db.session.commit()
          
          return jsonify({"mensagem": "Sucesso", "id": v_nova_api.id}), 201
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/Api/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_api_cliente(id):
      """
      Busca uma credencial de API específica pelo seu ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID único da credencial de API
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_api = ApiCliente.query.get(id)
          
          if not v_api:
              return jsonify({
                  "erro": "Não encontrado", 
                  "mensagem": f"Nenhum registro de API encontrado com o ID {id}"
              }), 404
          
          return jsonify(v_api.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/Api/get', methods=['GET'])
  @login_required
  def f_read_all_api_cliente():
      """
      Lista todas as credenciais de API cadastradas no sistema
      ---
      responses:
        200:
          description:
        500:
          description:
      """
      try:
          v_registros = ApiCliente.query.all()

          return jsonify([v_r.f_para_dicionario() for v_r in v_registros]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/Api/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_api_cliente(id):
      """
      Atualiza os dados de uma credencial de API existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID da credencial a ser atualizada
        - name: body
          in: body
          required: true
          schema:
            properties:
              idsentinela:
                type: integer
                example: 12
              usr:
                type: string
                example: "user_api_editado"
              senha:
                type: string
                example: "novasenha123"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
      """
      v_dados = request.get_json(silent=True)
      if not v_dados:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_api = ApiCliente.query.get(id)
      if not v_api:
          return jsonify({"erro": "Não encontrado", "mensagem": f"Credencial de ID {id} não localizada"}), 404

      v_dados.pop('id', None)
      v_dados.pop('idcliente', None)

      if 'usr' in v_dados and v_dados['usr'] != v_api.usr:
          v_usr_existe = ApiCliente.query.filter_by(usr=v_dados['usr']).first()
          if v_usr_existe:
              return jsonify({
                  "erro": "Usuário já existe",
                  "mensagem": f"O usuário '{v_dados['usr']}' já está sendo utilizado em outro registro"
              }), 409

      if 'idsentinela' in v_dados and v_dados['idsentinela'] != v_api.idsentinela:
          v_sentinela = db.session.get(AcessoExterno, v_dados['idsentinela'])
          if not v_sentinela:
              return jsonify({"erro": "Sentinela não encontrado", "mensagem": "O novo ID de sentinela informado não existe"}), 400
          
          if v_sentinela.id_empresa != v_api.idcliente:
              return jsonify({
                  "erro": "Conflito de vínculo",
                  "mensagem": "O novo sentinela informado não pertence à empresa desta credencial"
              }), 400
          v_api.idsentinela = v_dados['idsentinela']

      if 'usr' in v_dados: v_api.usr = v_dados['usr']
      
      if 'senha' in v_dados and v_dados['senha']:
          v_api.f_definir_senha(v_dados['senha'])

      try:
          db.session.commit()
          return jsonify({"mensagem": "Dados atualizados com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
    
  @v_app.route('/Empresa/Api/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_api_cliente(id):
      """
      Remove uma credencial de API do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID da credencial a ser removida
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_api = ApiCliente.query.get(id)
          
          if not v_api:
              return jsonify({
                  "erro": "Não encontrado", 
                  "mensagem": f"A credencial de ID {id} não existe e não pôde ser removida"
              }), 404

          db.session.delete(v_api)
          db.session.commit()
          
          return jsonify({"mensagem": "Credencial removida com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
  
  # ENDPOINTS DE CENTRO DE CUSTO

  @v_app.route('/Centrodecusto/add', methods=['POST'])
  @login_required
  def f_create_centro_custo():
      """
      Cadastra um novo centro de custo no sistema
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: CentroCusto
            required:
              - descricao
            properties:
              descricao:
                type: string
                example: "Departamento de TI"
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if not v_dados:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      v_descricao = v_dados.get('descricao')
      if not v_descricao or not str(v_descricao).strip():
          return jsonify({
              "erro": "Dados incompletos",
              "mensagem": "O campo 'descricao' é obrigatório e não pode estar vazio"
          }), 400

      v_descricao = str(v_descricao).strip()

      v_existe = CentroCusto.query.filter_by(descricao=v_descricao).first()
      if v_existe:
          return jsonify({
              "erro": "Conflito",
              "mensagem": f"O centro de custo '{v_descricao}' já está cadastrado"
          }), 409

      try:
          v_novo_centrocusto = CentroCusto(descricao=v_descricao)
          db.session.add(v_novo_centrocusto)
          db.session.commit()
          
          return jsonify({
              "mensagem": "Sucesso", 
              "id": v_novo_centrocusto.id
          }), 201
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Centrodecusto/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_centro_custo(id):
      """
      Busca um centro de custo específico pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_centrocusto = CentroCusto.query.get(id)
          
          if not v_centrocusto:
              return jsonify({
                  "erro": "Não encontrado", 
                  "mensagem": f"Centro de custo com ID {id} não localizado"
              }), 404
          
          return jsonify(v_centrocusto.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Centrodecusto/get', methods=['GET'])
  @login_required
  def f_read_all_centro_custo():
      """
      Lista todos os centros de custo cadastrados
      ---
      responses:
        200:
          description:
        500:
          description:
      """
      try:
          v_registros = CentroCusto.query.all()
          return jsonify([v_r.f_para_dicionario() for v_r in v_registros]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Centrodecusto/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_centro_custo(id):
      """
      Atualiza a descrição de um centro de custo existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              descricao:
                type: string
                example: "Nova descrição"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
      """
      v_centrocusto = CentroCusto.query.get(id)
      if not v_centrocusto:
          return jsonify({"erro": "Não encontrado", "mensagem": "Centro de custo não localizado"}), 404

      v_dados = request.get_json(silent=True)
      if not v_dados:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido"}), 400

      # Validação para impedir troca de ID
      if v_dados and 'id' in v_dados:
          if int(v_dados['id']) != id:
              return jsonify({
                  "erro": "Tentativa de alteração inválida",
                  "mensagem": "O ID enviado no corpo da requisição não coincide com o ID da URL"
              }), 400

      v_nova_descricao = v_dados.get('descricao')

      if not v_nova_descricao or not str(v_nova_descricao).strip():
          return jsonify({
              "erro": "Dados incompletos",
              "mensagem": "O campo 'descricao' é obrigatório para a atualização"
          }), 400

      v_nova_descricao = str(v_nova_descricao).strip()

      v_conflito = CentroCusto.query.filter(
          CentroCusto.descricao == v_nova_descricao, 
          CentroCusto.id != id
      ).first()

      if v_conflito:
          return jsonify({
              "erro": "Conflito",
              "mensagem": f"Já existe outro centro de custo cadastrado como '{v_nova_descricao}'"
          }), 409

      try:
          v_centrocusto.descricao = v_nova_descricao
          db.session.commit()
          
          return jsonify({
              "mensagem": "Sucesso", 
              "id": v_centrocusto.id
          }), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Centrodecusto/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_centro_custo(id):
      """
      Remove um centro de custo do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_centrocusto = CentroCusto.query.get(id)
          
          if not v_centrocusto:
              return jsonify({
                  "erro": "Não encontrado", 
                  "mensagem": f"O centro de custo de ID {id} não existe"
              }), 404

          v_vinculo = Financeiro.query.filter_by(centrocusto=id).first()
          if v_vinculo:
              return jsonify({
                  "erro": "Erro de integridade",
                  "mensagem": "Não é possível excluir este centro de custo pois ele possui lançamentos financeiros vinculados"
              }), 400

          db.session.delete(v_centrocusto)
          db.session.commit()
          
          return jsonify({"mensagem": "Sucesso", "id": id}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE VÍNCULO COLABORADOR-ACESSO

  @v_app.route('/Empresa/Colaborador/Acesso/add', methods=['POST'])
  @login_required
  def f_create_colaborador_acesso():
      """
      Registra um novo acesso de colaborador
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: ColaboradorAcesso
            required:
              - idcolaboradoremail
              - ip
              - data
              - estado
            properties:
              idcolaboradoremail:
                type: integer
                example: 1
              ip:
                type: string
                example: "192.168.1.50"
              data:
                type: string
                example: "23/04/2026"
              estado:
                type: integer
                example: 1
      responses:
        201:
          description:
        400:
          description:
        401:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido ou malformado"}), 400

      v_campos_obrigatorios = ['idcolaboradoremail', 'ip', 'data', 'estado']
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400

      if not isinstance(v_dados.get('idcolaboradoremail'), int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'idcolaboradoremail' deve ser um número inteiro"}), 400
      
      if not isinstance(v_dados.get('estado'), int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'estado' deve ser um número inteiro (smallint)"}), 400

      v_data_str = v_dados.get('data')
      v_data_objeto = f_validar_data(v_data_str)
      if not v_data_objeto:
          return jsonify({"erro": "Formato inválido", "mensagem": "Data deve ser DD/MM/YYYY"}), 400
      v_dados['data'] = v_data_objeto

      v_novo_acesso = ColaboradorAcesso(**v_dados)
        
      try:
          db.session.add(v_novo_acesso)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_novo_acesso.id}), 201
      except (TypeError, ValueError) as e:
          db.session.rollback()
          return jsonify({
              "erro": "Tipo de dado inválido", 
              "mensagem": "Um ou mais campos possuem valores incompatíveis com o banco de dados"
          }), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)
          if 'foreign key constraint fails' in v_erro_str.lower():
              return jsonify({
                  "erro": "Conflito de integridade",
                  "mensagem": "O idcolaboradoremail fornecido não existe na base de dados"
              }), 400
          return jsonify({"erro": "Erro de integridade", "detalhes": str(e.orig)}), 400      
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Empresa/Colaborador/Acesso/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_colaborador_acesso(id):
      """
      Busca um registro de acesso pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID único do registro de acesso
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_acesso = db.session.get(ColaboradorAcesso, id)

          if not v_acesso:
              return jsonify({"erro": "Não encontrado"}), 404
          
          return jsonify(v_acesso.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível conectar ao servidor"
          }), 503

  @v_app.route('/Empresa/Colaborador/Acesso/get', methods=['GET'])
  @login_required
  def f_read_all_colaborador_acessos():
      """
      Busca todos os registros de acessos cadastrados
      ---
      responses:
        200:
          description:
        503:
          description:
      """
      try:
          v_acessos = ColaboradorAcesso.query.all()
          
          v_lista_acessos = [v_a.f_para_dicionario() for v_a in v_acessos]
          
          return jsonify(v_lista_acessos), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível recuperar a lista de acessos"
          }), 503

  @v_app.route('/Empresa/Colaborador/Acesso/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_colaborador_acesso(id):
      """
      Atualiza dados de um registro de acesso existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              idcolaboradoremail:
                type: integer
                example: 1
              ip:
                type: string
                example: "172.16.0.10"
              data:
                type: string
                example: "24/04/2026"
              estado:
                type: integer
                example: 0
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_acesso = db.session.get(ColaboradorAcesso, id)

      if not v_acesso:
          return jsonify({"erro": "Não encontrado"}), 404
      
      v_novos_dados = request.get_json(silent=True)
      if v_novos_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400
      
      v_campos_permitidos = ['idcolaboradoremail', 'ip', 'data', 'estado']

      try:
          for v_chave, v_valor in v_novos_dados.items():
              if v_chave in v_campos_permitidos:
                  if v_chave in ['idcolaboradoremail', 'estado'] and not isinstance(v_valor, int):
                      raise TypeError(f"O campo {v_chave} deve ser um número inteiro")
                  
                  if v_chave == 'data' and v_valor:
                      v_data_objeto = f_validar_data(v_valor)
                      if not v_data_objeto:
                          return jsonify({"erro": "Data inválida", "mensagem": "Use DD/MM/YYYY"}), 400
                      v_acesso.data = v_data_objeto
                  else:
                      setattr(v_acesso, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except (ValueError, TypeError) as e:
          db.session.rollback()
          return jsonify({
              "erro": "Tipo de dado inválido", 
              "mensagem": str(e) if "deve ser" in str(e) else "Um ou mais campos possuem valores com tipo incorreto"
          }), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig).lower()
          if 'foreign key' in v_erro_str:
              return jsonify({
                  "erro": "Conflito", 
                  "mensagem": "O idcolaboradoremail fornecido não existe"
              }), 409
          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de integridade nos dados"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Empresa/Colaborador/Acesso/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_colaborador_acesso(id):
      """
      Remove um registro de acesso do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      try:
          v_acesso = db.session.get(ColaboradorAcesso, id)

          if not v_acesso:
              return jsonify({"erro": "Não encontrado"}), 404
            
          db.session.delete(v_acesso)
          db.session.commit()
          
          return jsonify({"mensagem": "Removido"}), 200
      except IntegrityError as e:
          db.session.rollback()
          return jsonify({
              "erro": "Conflito de integridade", 
              "mensagem": "Não é possível remover este registro devido a restrições no banco de dados"
          }), 409
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE CLIENTE DE HOTSPOT

  @v_app.route('/Empresa/HotspotClient/add', methods=['POST'])
  @login_required
  def f_create_hotspot_client():
      """
      Cadastra um novo cliente no hotspot
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: HotspotClient
            required:
              - nome
              - newsletter
              - idempresa
            properties:
              nome:
                type: string
                example: "Cliente Teste"
              email:
                type: string
                example: "cliente@gmail.com"
              cpf:
                type: string
                example: "12345678901"
              rg:
                type: string
                example: "12345678"
              newsletter:
                type: boolean
                example: true
              idempresa:
                type: integer
                example: 1
              data:
                type: string
                example: "28/04/2026 14:30:00"
              id_uuid_local_hotspot:
                type: string
                example: "uuid-1234-5678"
              telefone:
                type: string
                example: "11988887777"
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido ou malformado"}), 400

      v_campos_obrigatorios = ['nome', 'newsletter', 'idempresa']
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400

      if not isinstance(v_dados.get('idempresa'), int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'idempresa' deve ser um número inteiro"}), 400
      
      if not isinstance(v_dados.get('newsletter'), (bool, int)):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'newsletter' deve ser booleano"}), 400

      v_str_data = v_dados.pop('data', None)
      v_str_hora = v_dados.pop('hora', None)

      if v_str_data:
          try:
              # Usa a funcionalidade padrão para validação data/hora primeiro
              v_dados['data'] = datetime.datetime.strptime(v_str_data, '%d/%m/%Y %H:%M:%S')
          except ValueError:
              # Caso haja algum problema, tenta validar data e hora separadamente com as funções auxiliares e depois combina
              v_obj_data = f_validar_data(v_str_data)
              if not v_obj_data:
                  return jsonify({
                      "erro": "Formato inválido", 
                      "mensagem": "Use DD/MM/YYYY ou DD/MM/YYYY HH:MM:SS"
                  }), 400
              
              v_obj_hora = f_validar_hora(v_str_hora) if v_str_hora else datetime.time(0, 0, 0)
              v_dados['data'] = datetime.datetime.combine(v_obj_data, v_obj_hora)

      v_novo_cliente = HotspotClient(**v_dados)

      try:
          db.session.add(v_novo_cliente)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_novo_cliente.id}), 201
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig).lower()
          if 'foreign key' in v_erro_str:
              return jsonify({
                  "erro": "Conflito de integridade",
                  "mensagem": "O idempresa fornecido não existe"
              }), 400
          return jsonify({"erro": "Erro de integridade", "detalhes": str(e.orig)}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/HotspotClient/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_hotspot_client(id):
      """
      Busca um cliente de hotspot pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        503:
          description:
      """
      try:
          v_cliente = db.session.get(HotspotClient, id)

          if not v_cliente:
              return jsonify({"erro": "Não encontrado"}), 404
          
          return jsonify(v_cliente.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível conectar ao servidor"
          }), 503

  @v_app.route('/Empresa/HotspotClient/get', methods=['GET'])
  @login_required
  def f_read_all_hotspot_clients():
      """
      Busca todos os clientes de hotspot cadastrados
      ---
      responses:
        200:
          description:
        503:
          description:
      """
      try:
          v_clientes = HotspotClient.query.all()
          
          v_lista_clientes = [v_c.f_para_dicionario() for v_c in v_clientes]
          
          return jsonify(v_lista_clientes), 200
      except Exception as e:
          return jsonify({
              "erro": "Erro de banco de dados", 
              "mensagem": "Não foi possível recuperar a lista de clientes"
          }), 503

  @v_app.route('/Empresa/HotspotClient/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_hotspot_client(id):
      """
      Atualiza os dados de um cliente do hotspot
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              nome:
                type: string
                example: "Novo Teste"
              email:
                type: string
                example: "novoteste@gmail.com"
              cpf:
                type: string
                example: "09876543210"
              rg:
                type: string
                example: "87654321"
              newsletter:
                type: boolean
                example: false
              idempresa:
                type: integer
                example: 2
              data:
                type: string
                example: "28/04/2026 10:30:00"
              id_uuid_local_hotspot:
                type: string
                example: "uuid-8765-4321"
              telefone:
                type: string
                example: "12987887787"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_cliente = db.session.get(HotspotClient, id)

          if not v_cliente:
              return jsonify({"erro": "Não encontrado"}), 404

          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "JSON malformado"}), 400

          v_dados.pop('id', None)

          v_str_data = v_dados.pop('data', None)
      
          if v_str_data:
              try:
                  v_cliente.data = datetime.datetime.strptime(v_str_data, '%d/%m/%Y %H:%M:%S')
              except ValueError:
                  return jsonify({
                      "erro": "Formato inválido", 
                      "mensagem": "Para atualizar o campo data, use o formato DD/MM/YYYY HH:MM:SS"
                  }), 400

          if 'idempresa' in v_dados:
            if not db.session.get(Empresa, v_dados['idempresa']):
                return jsonify({"erro": "Conflito", "mensagem": "A empresa informada não existe"}), 400

          for v_chave, v_valor in v_dados.items():
              if hasattr(v_cliente, v_chave):
                  setattr(v_cliente, v_chave, v_valor)

          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except IntegrityError as e:
          db.session.rollback()
          return jsonify({"erro": "Erro de integridade", "mensagem": "Verifique se o idempresa é válido"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/HotspotClient/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_hotspot_client(id):
      """
      Remove um cliente do hotspot
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      try:
          v_cliente = db.session.get(HotspotClient, id)

          if not v_cliente:
              return jsonify({"erro": "Não encontrado"}), 404
            
          db.session.delete(v_cliente)
          db.session.commit()
          
          return jsonify({"mensagem": "Removido"}), 200
      except IntegrityError as e:
          db.session.rollback()
          return jsonify({
              "erro": "Conflito de integridade", 
              "mensagem": "Não é possível remover este registro devido a restrições no banco de dados"
          }), 409 
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  # ENDPOINTS DE LOCAL DE HOTSPOT

  @v_app.route('/Empresa/HotspotLocal/add', methods=['POST'])
  @login_required
  def f_create_hotspot_local():
      """
      Cadastra um novo local de hotspot
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: HotspotLocal
            required:
              - id_uuid_local_hotspot
              - id_empresa
              - descricao
              - metodo
            properties:
              id_uuid_local_hotspot:
                type: string
                example: "lobby-principal-01"
              id_empresa:
                type: integer
                example: 2
              descricao:
                type: string
                example: "Roteador da recepção"
              metodo:
                type: integer
                example: 2
              url:
                type: string
                example: "http://192.168.88.1/login"
              api_token:
                type: string
                example: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
              id_template:
                type: string
                example: "template_dark_mode_v2"
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "JSON malformado"}), 400

          v_campos_obrigatorios = ['id_uuid_local_hotspot', 'id_empresa', 'descricao', 'metodo']
          v_faltantes = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

          if v_faltantes:
              return jsonify({
                  "erro": "Campos obrigatórios ausentes",
                  "campos_faltantes": v_faltantes
              }), 400

          v_novo_local = HotspotLocal(**v_dados)
          
          db.session.add(v_novo_local)
          db.session.commit()

          return jsonify({
              "mensagem": "Cadastrado com sucesso",
              "id": v_novo_local.id
          }), 201
      except IntegrityError as e:
          db.session.rollback()

          return jsonify({
              "erro": "Erro de integridade",
              "mensagem": "Verifique se a empresa informada existe ou se o UUID já está em uso"
          }), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/HotspotLocal/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_hotspot_local(id):
      """
      Busca um local de hotspot específico pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_local = db.session.get(HotspotLocal, id)
      if not v_local:
          return jsonify({"erro": "Não encontrado"}), 404
      
      return jsonify(v_local.f_para_dicionario()), 200

  @v_app.route('/Empresa/HotspotLocal/get', methods=['GET'])
  @login_required
  def f_read_all_hotspot_locais():
      """
      Lista todos os locais de hotspot filtrados por empresa
      ---
      parameters:
        - name: id_empresa
          in: query
          type: integer
          required: true
          description: ID da empresa para filtrar os locais
      responses:
        200:
          description:
        400:
          description:
        500:
          description:
      """
      v_id_empresa = request.args.get('id_empresa', type=int)

      if not v_id_empresa:
          return jsonify({
              "erro": "Faltam parâmetros", 
              "mensagem": "O parâmetro id_empresa é obrigatório na URL"
          }), 400

      try:
          v_locais = HotspotLocal.query.filter_by(id_empresa=v_id_empresa).all()

          return jsonify([v_l.f_para_dicionario() for v_l in v_locais]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Empresa/HotspotLocal/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_hotspot_local(id):
      """
      Atualiza as configurações de um local de hotspot
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              id_uuid_local_hotspot:
                type: string
                example: "novo-setor-01"
              id_empresa:
                type: integer
                example: 1
              descricao:
                type: string
                example: "Roteador do novo setor"
              metodo:
                type: integer
                example: 1
              url:
                type: string
                example: "http://192.168.67.2/login"
              api_token:
                type: string
                example: "olJbrGciOiJIUzI2NiIsInR5cCI7IxdAVCJ10"
              id_template:
                type: string
                example: "template_v3"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
      """
      try:
          v_local = db.session.get(HotspotLocal, id)

          if not v_local:
              return jsonify({"erro": "Não encontrado"}), 404

          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "JSON malformado"}), 400

          v_dados.pop('id', None)
          
          if 'id_empresa' in v_dados:
              if not db.session.get(Empresa, v_dados['id_empresa']):
                  return jsonify({"erro": "Conflito", "mensagem": "A nova empresa informada não existe"}), 400

          for v_chave, v_valor in v_dados.items():
              if hasattr(v_local, v_chave):
                  setattr(v_local, v_chave, v_valor)

          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Empresa/HotspotLocal/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_hotspot_local(id):
      """
      Remove um local de hotspot permanentemente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_local = db.session.get(HotspotLocal, id)

          if not v_local:
              return jsonify({"erro": "Não encontrado"}), 404

          db.session.delete(v_local)
          db.session.commit()

          return jsonify({"mensagem": "Removido"}), 200
      except IntegrityError:
          db.session.rollback()
          return jsonify({
              "erro": "Conflito de integridade",
              "mensagem": "Não é possível remover este registro devido a restrições no banco de dados"
          }), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE TERMOS DO HOTSPOT

  @v_app.route('/Empresa/HotspotTermos/add', methods=['POST'])
  @login_required
  def f_create_hotspot_termos():
      """
      Cadastra novos termos de uso para o hotspot de uma empresa
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: HotspotTermos
            required:
              - idempresa
              - termos
            properties:
              idempresa:
                type: integer
                example: 2
              termos:
                type: string
                example: "Ao utilizar este Wi-Fi, você concorda com a nossa política de privacidade"
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "JSON malformado"}), 400

          v_campos_obrigatorios = ['idempresa', 'termos']
          v_faltantes = [campo for campo in v_campos_obrigatorios if campo not in v_dados or not v_dados.get(campo)]

          if v_faltantes:
              return jsonify({
                  "erro": "Campos obrigatórios ausentes",
                  "campos_faltantes": v_faltantes
              }), 400

          v_novos_termos = HotspotTermos(**v_dados)
          
          db.session.add(v_novos_termos)
          db.session.commit()

          return jsonify({
              "mensagem": "Termos cadastrados com sucesso",
              "id": v_novos_termos.id
          }), 201
      except IntegrityError:
          db.session.rollback()
          return jsonify({
              "erro": "Erro de integridade",
              "mensagem": "Verifique se o idempresa informado existe no cadastro de empresas"
          }), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Empresa/HotspotTermos/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_hotspot_termos(id):
      """
      Busca um registro de termos de uso específico pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_termo = db.session.get(HotspotTermos, id)
      if not v_termo:
          return jsonify({"erro": "Não encontrado"}), 404
      
      return jsonify(v_termo.f_para_dicionario()), 200

  @v_app.route('/Empresa/HotspotTermos/get', methods=['GET'])
  @login_required
  def f_read_all_hotspot_termos():
      """
      Lista todos os termos cadastrados para uma empresa específica
      ---
      parameters:
        - name: idempresa
          in: query
          type: integer
          required: true
          description: ID da empresa para filtrar os termos
      responses:
        200:
          description:
        400:
          description:
        500:
          description:
      """
      v_id_empresa = request.args.get('idempresa', type=int)

      if not v_id_empresa:
          return jsonify({
              "erro": "Faltam parâmetros", 
              "mensagem": "O parâmetro idempresa é obrigatório na URL"
          }), 400

      try:
          v_termos = HotspotTermos.query.filter_by(idempresa=v_id_empresa).all()

          return jsonify([v_t.f_para_dicionario() for v_t in v_termos]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Empresa/HotspotTermos/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_hotspot_termos(id):
      """
      Atualiza o conteúdo de um termo de uso existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              termos:
                type: string
                example: "Texto atualizado dos termos de uso, para conformidade com o LGPD"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
      """
      try:
          v_termo = db.session.get(HotspotTermos, id)
          if not v_termo:
              return jsonify({"erro": "Não encontrado"}), 404

          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "JSON malformado"}), 400

          v_dados.pop('id', None)
          v_dados.pop('idempresa', None) # Os termos não devem ser aplicados a outra empresa

          for v_chave, v_valor in v_dados.items():
              if hasattr(v_termo, v_chave):
                  setattr(v_termo, v_chave, v_valor)

          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/HotspotTermos/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_hotspot_termos(id):
      """
      Remove um registro de termos de uso
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_termo = db.session.get(HotspotTermos, id)
          if not v_termo:
              return jsonify({"erro": "Não encontrado"}), 404

          db.session.delete(v_termo)
          db.session.commit()

          return jsonify({"mensagem": "Removido"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE VÍNCULO USUÁRIO-EMPRESA

  @v_app.route('/Empresa/Usuario/add', methods=['POST'])
  @login_required
  def f_create_usuario_empresa():
      """
      Vincula um usuário a uma empresa
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: UsuarioEmpresa
            required:
              - idempresa
              - idusuario
            properties:
              idempresa:
                type: integer
                example: 2
              idusuario:
                type: integer
                example: 1
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "JSON malformado"}), 400

          v_id_empresa = v_dados.get('idempresa')
          v_id_usuario = v_dados.get('idusuario')

          if not v_id_empresa or not v_id_usuario:
              return jsonify({"erro": "Campos obrigatórios", "mensagem": "idempresa e idusuario são necessários"}), 400

          # Prevenção de duplicidade
          v_existente = UsuarioEmpresa.query.filter_by(
              idempresa=v_id_empresa, 
              idusuario=v_id_usuario
          ).first()
          
          if v_existente:
              return jsonify({
                  "erro": "Vínculo já existe", 
                  "mensagem": "Este usuário já possui acesso a esta empresa"
              }), 400
          
          if not db.session.get(Empresa, v_id_empresa) or not db.session.get(Usuario, v_id_usuario):
              return jsonify({"erro": "Inconsistência", "mensagem": "Empresa ou usuário informado não existe"}), 400

          v_novo_vinculo = UsuarioEmpresa(idempresa=v_id_empresa, idusuario=v_id_usuario)
          db.session.add(v_novo_vinculo)
          db.session.commit()

          return jsonify({
              "mensagem": "Vínculo estabelecido com sucesso",
              "id": v_novo_vinculo.id
          }), 201
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Empresa/Usuario/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_vinculo_usuario(id):
      """
      Busca um vínculo empresa-usuário específico pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_vinculo = db.session.get(UsuarioEmpresa, id)
      if not v_vinculo:
          return jsonify({"erro": "Não encontrado"}), 404
      
      return jsonify(v_vinculo.f_para_dicionario()), 200

  @v_app.route('/Empresa/Usuario/get', methods=['GET'])
  @login_required
  def f_read_all_vinculos_empresa():
      """
      Lista todos os usuários vinculados a uma empresa específica
      ---
      parameters:
        - name: idempresa
          in: query
          type: integer
          required: true
          description: ID da empresa para filtrar os usuários vinculados
      responses:
        200:
          description:
        400:
          description:
      """
      v_id_empresa = request.args.get('idempresa', type=int)

      if not v_id_empresa:
          return jsonify({
              "erro": "Faltam parâmetros", 
              "mensagem": "O parâmetro idempresa é obrigatório na URL"
          }), 400

      try:
          v_vinculos = UsuarioEmpresa.query.filter_by(idempresa=v_id_empresa).all()

          return jsonify([v_v.f_para_dicionario() for v_v in v_vinculos]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/Usuario/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_usuario_empresa(id):
      """
      Atualiza um vínculo usuário-empresa
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              idempresa:
                type: integer
                example: 1
              idusuario:
                type: integer
                example: 2
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
      """
      try:
          v_vinculo = db.session.get(UsuarioEmpresa, id)
          if not v_vinculo:
              return jsonify({"erro": "Não encontrado"}), 404

          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida"}), 400

          v_novo_id_emp = v_dados.get('idempresa')
          v_novo_id_usr = v_dados.get('idusuario')

          if v_novo_id_emp and not db.session.get(Empresa, v_novo_id_emp):
              return jsonify({"erro": "Empresa inexistente"}), 400
          if v_novo_id_usr and not db.session.get(Usuario, v_novo_id_usr):
              return jsonify({"erro": "Usuário inexistente"}), 400

          for v_chave, v_valor in v_dados.items():
              if hasattr(v_vinculo, v_chave):
                  setattr(v_vinculo, v_chave, v_valor)

          db.session.commit()
          return jsonify({"mensagem": "Vínculo atualizado"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Empresa/Usuario/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_usuario_empresa(id):
      """
      Remove o vínculo de um usuário a uma empresa
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      try:
          v_vinculo = db.session.get(UsuarioEmpresa, id)
          if not v_vinculo:
              return jsonify({"erro": "Não encontrado"}), 404

          db.session.delete(v_vinculo)
          db.session.commit()

          return jsonify({"mensagem": "Vínculo removido"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE NÍVEL DE ACESSO

  @v_app.route('/Nacesso/add', methods=['POST'])
  @login_required
  def f_add_nacesso():
      """
      Cadastra um novo perfil de nível de acesso
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: Nacesso
            required:
              - nome
            properties:
              nome:
                type: string
                example: "Administrador"
              item_menu:
                type: integer
                example: 1
              pagina:
                type: integer
                example: 1
              usuario:
                type: integer
                example: 1
              colaborador:
                type: integer
                example: 1
              departamento:
                type: integer
                example: 1
              col_departamento:
                type: integer
                example: 1
              financeiro:
                type: integer
                example: 1
              empresa:
                type: integer
                example: 1
              usr_empresa:
                type: integer
                example: 1
              mod_os:
                type: integer
                example: 1
              os:
                type: integer
                example: 1
              marketing:
                type: integer
                example: 1
              analitico:
                type: integer
                example: 1
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida"}), 400

          if not v_dados.get('nome'):
              return jsonify({"erro": "Nome é obrigatório"}), 400

          v_campos_binarios = [
              'item_menu', 'pagina', 'usuario', 'colaborador', 'departamento',
              'col_departamento', 'financeiro', 'empresa', 'usr_empresa',
              'mod_os', 'os', 'marketing', 'analitico'
          ]

          # Garante que apenas 0 ou 1 sejam inseridos (se o campo não vier no JSON, o padrão do banco é 0)
          for v_campo in v_campos_binarios:
              if v_campo in v_dados:
                  v_valor = v_dados[v_campo]
                  if v_valor not in [0, 1]:
                      return jsonify({
                          "erro": f"Valor inválido no campo {v_campo}",
                          "mensagem": "Este campo aceita apenas 0 (não) ou 1 (sim)"
                      }), 400

          v_novo_nivel = NivelAcesso(**v_dados)
          
          db.session.add(v_novo_nivel)
          db.session.commit()

          return jsonify({
              "mensagem": "Nível de acesso cadastrado com sucesso",
              "id": v_novo_nivel.id
          }), 201
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Nacesso/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_nacesso(id):
      """
      Busca um perfil de acesso específico pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_nivel = db.session.get(NivelAcesso, id)
      if not v_nivel:
          return jsonify({"erro": "Não encontrado", "mensagem": "Nível de acesso inexistente"}), 404
      
      return jsonify(v_nivel.f_para_dicionario()), 200

  @v_app.route('/Nacesso/get', methods=['GET'])
  @login_required
  def f_read_all_nacesso():
      """
      Lista todos os perfis de acesso cadastrados no sistema
      ---
      responses:
        200:
          description:
        500:
          description:
      """
      try:
          v_niveis = NivelAcesso.query.order_by(NivelAcesso.nome).all()
          
          return jsonify([v_n.f_para_dicionario() for v_n in v_niveis]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Nacesso/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_nacesso(id):
      """
      Atualiza um perfil de acesso existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              nome:
                type: string
                example: "Gerente"
              item_menu:
                type: integer
                example: 0
              pagina:
                type: integer
                example: 0
              usuario:
                type: integer
                example: 0
              colaborador:
                type: integer
                example: 0
              departamento:
                type: integer
                example: 0
              col_departamento:
                type: integer
                example: 0
              financeiro:
                type: integer
                example: 0
              empresa:
                type: integer
                example: 0
              usr_empresa:
                type: integer
                example: 0
              mod_os:
                type: integer
                example: 0
              os:
                type: integer
                example: 0
              marketing:
                type: integer
                example: 0
              analitico:
                type: integer
                example: 0
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_nivel = db.session.get(NivelAcesso, id)
          if not v_nivel:
              return jsonify({"erro": "Não encontrado"}), 404

          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida"}), 400

          v_campos_binarios = [
              'item_menu', 'pagina', 'usuario', 'colaborador', 'departamento',
              'col_departamento', 'financeiro', 'empresa', 'usr_empresa',
              'mod_os', 'os', 'marketing', 'analitico'
          ]

          for v_campo in v_campos_binarios:
              if v_campo in v_dados:
                  if v_dados[v_campo] not in [0, 1]:
                      return jsonify({
                          "erro": f"Valor inválido em {v_campo}",
                          "mensagem": "Apenas 0 ou 1 são permitidos"
                      }), 400

          for v_chave, v_valor in v_dados.items():
              if hasattr(v_nivel, v_chave):
                  setattr(v_nivel, v_chave, v_valor)

          db.session.commit()
          return jsonify({"mensagem": "Perfil atualizado com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Nacesso/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_nacesso(id):
      """
      Remove um perfil de acesso
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      try:
          v_nivel = db.session.get(NivelAcesso, id)
          if not v_nivel:
              return jsonify({"erro": "Não encontrado"}), 404

          db.session.delete(v_nivel)
          db.session.commit()

          return jsonify({"mensagem": "Perfil removido com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE ORDEM DE SERVIÇO

  @v_app.route('/Os/add', methods=['POST'])
  @login_required
  def f_create_os():
      """
      Cria uma nova ordem de serviço
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: Os
            required:
              - idempresa
              - predescricao
              - descricao
            properties:
              idempresa:
                type: integer
                example: 1
              iddepartamento:
                type: integer
                example: 1
              idusrempresa:
                type: integer
                description: ID do vínculo usuário-empresa (quem abriu)
                example: 1
              idcolaborador:
                type: integer
                example: 1
              predescricao:
                type: string
                maxLength: 100
                description: Título ou resumo da OS
                example: "Lorem ipsum"
              descricao:
                type: string
                description: Detalhamento técnico da OS
                example: "Lorem ipsum dolor sit amet..."
              estado:
                type: boolean
                default: true
              peso:
                type: integer
                description: Vai de 1 a 4
                example: 1
              usrfeedback:
                type: integer
                example: 5
              usrobservacao:
                type: string
                example: "Cliente solicitou pressa pois o setor financeiro está parado"
              colaborador:
                type: string
                maxLength: 50
                example: "Técnico Fulano de Tal"
              flag:
                type: string
                maxLength: 255
                example: "URGENTE_ALTA_PRIORIDADE"
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
        502:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida"}), 400

          campos_obrigatorios = ['idempresa', 'predescricao', 'descricao']
          for campo in campos_obrigatorios:
              if v_dados.get(campo) is None or str(v_dados.get(campo)).strip() == "":
                  return jsonify({"erro": f"O campo '{campo}' é obrigatório"}), 400
          
          v_id_empresa = v_dados.get('idempresa')

          # Captura o cabeçalho de autenticação atual para repassar à rota de empresa
          v_token = request.headers.get('Authorization')
          v_headers = {'Authorization': v_token} if v_token else {}

          v_cookies = request.cookies

          # Constrói a URL interna para o endpoint de empresas
          v_url_empresa = f"{request.host_url}Empresa/get/{v_id_empresa}"

          try:
              v_resposta = requests.get(v_url_empresa, headers=v_headers, cookies=v_cookies, timeout=5)
              
              if v_resposta.status_code == 404:
                  return jsonify({"erro": "Empresa inválida", "mensagem": "A empresa informada não existe"}), 400
              elif v_resposta.status_code != 200:
                  return jsonify({"erro": "Falha de validação", "mensagem": "Não foi possível verificar o status da empresa no momento"}), 502

              v_dados_empresa = v_resposta.json()

              # Valida se a empresa está com estado ativo
              if v_dados_empresa.get('estado') is not True:
                  return jsonify({
                      "erro": "Empresa inativa", 
                      "mensagem": "Não é permitido criar ordens de serviço para empresas com estado inativo"
                  }), 400

          except requests.exceptions.RequestException as e:
              return jsonify({"erro": "Erro de comunicação", "mensagem": f"Não foi possível contactar o serviço de empresas: {str(e)}"}), 502

          v_peso = v_dados.get('peso')
          if v_peso is not None and v_peso not in [1, 2, 3, 4]:
              return jsonify({"erro": "O campo 'peso' deve ser um número inteiro entre 1 e 4"}), 400

          # Pega o momento exato da abertura de forma automática
          v_agora = datetime.datetime.now()

          v_nova_os = OrdemServico(
              idempresa=v_id_empresa,
              iddepartamento=v_dados.get('iddepartamento'),
              idusrempresa=v_dados.get('idusrempresa'),
              idcolaborador=v_dados.get('idcolaborador'),
              usrfeedback=v_dados.get('usrfeedback'),
              estado=v_dados.get('estado', True),
              predescricao=v_dados.get('predescricao'),
              descricao=v_dados.get('descricao'),
              peso=v_dados.get('peso'),
              usrobservacao=v_dados.get('usrobservacao'),
              colaborador=v_dados.get('colaborador'),
              flag=v_dados.get('flag'),
              dataabertura=v_agora.date(),
              horaabertura=v_agora.time(),
              idagendamento=None,
              dataagendamento=None,
              horaagendamento=None,
              dataconclusao=None,
              horaconclusao=None
          )

          db.session.add(v_nova_os)
          db.session.commit()

          return jsonify({
              "mensagem": "Ordem de serviço criada com sucesso",
              "id": v_nova_os.id
          }), 201
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
  
  @v_app.route('/Os/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_os(id):
      """
      Busca os detalhes de uma ordem de serviço específica
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_os = db.session.get(OrdemServico, id)
          if not v_os:
              return jsonify({"erro": "Não encontrado", "mensagem": "OS inexistente"}), 404

          return jsonify(v_os.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Os/get', methods=['GET'])
  @login_required
  def f_read_all_os():
      """
      Busca todas as ordens de serviço, ou busca por filtros se eles tiverem sido passados
      ---
      parameters:
        - name: body
          in: body
          required: false
          schema:
            type: object
            properties:
              dataconclusao:
                oneOf:
                  - type: string
                    example: "22/05/2026"
                  - type: array
                    items:
                      type: string
                    example: ["20/05/2026", "25/05/2026"]
              dataabertura:
                oneOf:
                  - type: string
                    example: "19/05/2026"
                  - type: array
                    items:
                      type: string
                    example: ["15/05/2026", "20/05/2026"]
              palavrachave:
                type: string
                example: "manutenção"
              sprint:
                type: integer
                example: 2
              idempresa:
                type: integer
                example: 1
              estado:
                type: integer
                enum: [0, 1]
                example: 1
      responses:
        200:
          description:
        400:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True) or {}
      
      v_novos_filtros = ['dataconclusao', 'dataabertura', 'palavrachave', 'sprint', 'idempresa', 'estado']
      v_usando_filtros = any(v_campo in v_dados for v_campo in v_novos_filtros)

      try:
          # Fluxo padrão (caso nenhum filtro tenha sido enviado)
          if not v_usando_filtros:
              v_id_empresa = request.args.get('idempresa')

              if not v_id_empresa:
                  return jsonify({"erro": "Requisição inválida", "mensagem": "O parâmetro idempresa é obrigatório"}), 400

              # Busca as OSs daquela empresa, ordenando pelas mais recentes (data de abertura)
              v_lista_os = OrdemServico.query.filter_by(idempresa=v_id_empresa).order_by(OrdemServico.dataabertura.desc()).all()

              return jsonify([v_item.f_para_dicionario() for v_item in v_lista_os]), 200

          # Fluxo com filtros
          v_query = OrdemServico.query

          # Filtro 1: data de conclusão
          v_dataconclusao_raw = v_dados.get('dataconclusao')
          if v_dataconclusao_raw:
              if isinstance(v_dataconclusao_raw, list) and len(v_dataconclusao_raw) == 2:
                  v_data_inicio = f_validar_data(v_dataconclusao_raw[0])
                  v_data_fim = f_validar_data(v_dataconclusao_raw[1])
                  if v_data_inicio and v_data_fim:
                      v_query = v_query.filter(OrdemServico.dataconclusao.between(v_data_inicio, v_data_fim))
              else:
                  v_data_fixa = f_validar_data(v_dataconclusao_raw)
                  if v_data_fixa:
                      v_query = v_query.filter(OrdemServico.dataconclusao == v_data_fixa)

          # Filtro 2: data de abertura
          v_dataabertura_raw = v_dados.get('dataabertura')
          if v_dataabertura_raw:
              if isinstance(v_dataabertura_raw, list) and len(v_dataabertura_raw) == 2:
                  v_data_inicio = f_validar_data(v_dataabertura_raw[0])
                  v_data_fim = f_validar_data(v_dataabertura_raw[1])
                  if v_data_inicio and v_data_fim:
                      v_query = v_query.filter(OrdemServico.dataabertura.between(v_data_inicio, v_data_fim))
              else:
                  v_data_fixa = f_validar_data(v_dataabertura_raw)
                  if v_data_fixa:
                      v_query = v_query.filter(OrdemServico.dataabertura == v_data_fixa)

          # Filtro 3: sprint (colaborador que estava com a OS)
          v_sprint = v_dados.get('sprint')
          if v_sprint is not None:
              v_query = v_query.filter(OrdemServico.idcolaborador == v_sprint)

          # Filtro 4: idempresa
          v_idempresa = v_dados.get('idempresa')
          if v_idempresa is not None:
              v_query = v_query.filter(OrdemServico.idempresa == v_idempresa)

          # Filtro 5: estado (aberto: 1, concluído: 0)
          v_estado = v_dados.get('estado')
          if v_estado is not None:
              if v_estado == 1:
                  v_query = v_query.filter(OrdemServico.estado == True)
              elif v_estado == 0:
                  v_query = v_query.filter(OrdemServico.estado == False)

          v_resultado_os = v_query.all()
          v_lista_ranking = []
          
          v_palavra_chave = v_dados.get('palavrachave')
          v_termo_pesquisa = str(v_palavra_chave).lower().strip() if v_palavra_chave else None

          for v_os in v_resultado_os:
              v_movimentacoes = MovimentacaoOS.query.filter_by(idos=v_os.id).all()
              v_contador_palavras = 0
              
              # Se uma palavra-chave foi fornecida, é feita a contagem quantificada
              if v_termo_pesquisa:
                  v_texto_predescricao = str(v_os.predescricao or "").lower()
                  v_texto_descricao = str(v_os.descricao or "").lower()
                  
                  v_contador_palavras += v_texto_predescricao.count(v_termo_pesquisa)
                  v_contador_palavras += v_texto_descricao.count(v_termo_pesquisa)
                  
                  for v_mov in v_movimentacoes:
                      v_texto_mov = str(v_mov.descricao or "").lower()
                      v_contador_palavras += v_texto_mov.count(v_termo_pesquisa)
                  
                  if v_contador_palavras == 0:
                      continue
              
              v_lista_ranking.append({
                  "os": v_os.id,
                  "dataconclusao": v_os.dataconclusao.strftime('%d/%m/%Y') if v_os.dataconclusao else None,
                  "contador de palavras-chave": v_contador_palavras
              })

          # Ordenação/ranking
          import datetime as dt_mod
          v_data_minima = dt_mod.date(1970, 1, 1)
          
          v_lista_ranking.sort(
              key=lambda x: (
                  x["contador de palavras-chave"],
                  dt_mod.datetime.strptime(x["dataconclusao"], '%d/%m/%Y').date() if x["dataconclusao"] else v_data_minima
              ),
              reverse=True
          )

          return jsonify(v_lista_ranking), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Os/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_os(id):
      """
      Atualiza uma ordem de serviço existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            required:
              - idempresa
              - predescricao
              - descricao
              - dataagendamento
            properties:
              idempresa:
                type: integer
                example: 2
              iddepartamento:
                type: integer
                example: 2
              idusrempresa:
                type: integer
                description: ID do vínculo usuário-empresa (quem abriu)
                example: 2
              idcolaborador:
                type: integer
                example: 2
              predescricao:
                type: string
                maxLength: 100
                description: Título ou resumo da OS
                example: "Ipsum lorem"
              descricao:
                type: string
                description: Detalhamento técnico da OS
                example: "Ipsum lorem dolor sit amet..."
              estado:
                type: boolean
                default: false
              peso:
                type: integer
                description: Vai de 1 a 4
                example: 2
              usrfeedback:
                type: integer
                example: 4
              usrobservacao:
                type: string
                example: "Cliente solicitou X, Y e Z"
              colaborador:
                type: string
                maxLength: 50
                example: "Técnico Beltrano da Silva"
              flag:
                type: string
                maxLength: 255
                example: "BAIXA_PRIORIDADE"
              dataabertura:
                type: string
                example: "19/05/2026"
              horaabertura:
                type: string
                example: "10:00:00"
              dataagendamento:
                type: string
                example: "20/05/2026"
              horaagendamento:
                type: string
                example: "11:00:00"
              idagendamento:
                type: integer
                example: 1
              dataconclusao:
                type: string
                example: "22/05/2026"
              horaconclusao:
                type: string
                example: "15:00:00"
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
      """
      try:
          v_os = db.session.get(OrdemServico, id)
          if not v_os:
              return jsonify({"erro": "Não encontrado", "mensagem": "Ordem de serviço inexistente"}), 404

          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida"}), 400

          campos_obrigatorios = ['idempresa', 'predescricao', 'descricao', 'dataagendamento']
          for campo in campos_obrigatorios:
              if v_dados.get(campo) is None or str(v_dados.get(campo)).strip() == "":
                  return jsonify({"erro": f"O campo '{campo}' é obrigatório e não pode ser vazio"}), 400

          v_peso = v_dados.get('peso')
          if v_peso is not None and v_peso not in [1, 2, 3, 4]:
              return jsonify({"erro": "O campo 'peso' deve ser um número inteiro entre 1 e 4."}), 400

          # Mapeamento de campos que precisam de validação especial (data/hora)
          v_campos_data = ['dataagendamento', 'dataabertura', 'dataconclusao']
          v_campos_hora = ['horaagendamento', 'horaabertura', 'horaconclusao']

          v_peso_alterado = False

          for v_chave, v_valor in v_dados.items():
              if v_chave in ['dataestimada', 'horaestimada']:
                  continue
              
              if hasattr(v_os, v_chave):
                  if v_chave in v_campos_data:
                      setattr(v_os, v_chave, f_validar_data(v_valor))
                  elif v_chave in v_campos_hora:
                      setattr(v_os, v_chave, f_validar_hora(v_valor))
                  else:
                      setattr(v_os, v_chave, v_valor)
                  
                  if v_chave == 'peso':
                      v_peso_alterado = True

          if v_peso_alterado:
              v_os.atualizar_prazos_estimados()

          db.session.commit()
          return jsonify({"mensagem": "Ordem de serviço atualizada com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
    
  @v_app.route('/Os/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_os(id):
      """
      Exclui permanentemente uma ordem de serviço
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      try:
          v_os = db.session.get(OrdemServico, id)
          
          if not v_os:
              return jsonify({"erro": "Não encontrado", "mensagem": "Ordem de serviço não encontrada"}), 404

          # Verificação de segurança
          v_tem_financeiro = Financeiro.query.filter_by(os=id).first()
          if v_tem_financeiro:
              return jsonify({"erro": "Conflito", "mensagem": "Não é possível excluir OS com lançamentos financeiros ativos"}), 409

          db.session.delete(v_os)
          db.session.commit()

          return jsonify({"mensagem": f"Ordem de serviço #{id} excluída com sucesso"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
  
  # ENDPOINTS DE MOVIMENTAÇÃO DE OS

  @v_app.route('/Os/Movimentacao/add', methods=['POST'])
  @login_required
  def f_create_movimentacao_os():
      """
      Cadastra uma nova movimentação de ordem de serviço
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: MovimentacaoOS
            required:
              - idos
              - datamov
              - descricao
              - visivel
            properties:
              idos:
                type: integer
                example: 1
              idcolaborador:
                type: integer
                example: 1
              datamov:
                type: string
                example: "21/05/2026"
              descricao:
                type: string
                example: "Troca de roteador queimado realizada e testes de conectividade concluídos com sucesso"
              visivel:
                type: integer
                example: 1
      responses:
        201:
          description:
        400:
          description:
        500:
          description:
      """
      v_dados = request.get_json(silent=True)
      if v_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "JSON não fornecido ou malformado"}), 400

      v_campos_obrigatorios = ['idos', 'datamov', 'descricao', 'visivel']
      v_invalidos = [campo for campo in v_campos_obrigatorios if campo not in v_dados or v_dados.get(campo) is None]

      if v_invalidos:
          return jsonify({
              "erro": "Dados incompletos",
              "campos_faltantes": v_invalidos,
              "mensagem": f"Os campos {', '.join(v_invalidos)} são obrigatórios"
          }), 400
      
      if not isinstance(v_dados.get('idos'), int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'idos' deve ser um número inteiro"}), 400

      if v_dados.get('idcolaborador') is not None and not isinstance(v_dados.get('idcolaborador'), int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'idcolaborador' deve ser um número inteiro"}), 400

      if not isinstance(v_dados.get('visivel'), int):
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": "O campo 'visivel' deve ser um número inteiro"}), 400

      v_data_mov_str = v_dados.get('datamov')
      v_data_objeto = f_validar_data(v_data_mov_str)
      if not v_data_objeto:
          return jsonify({"erro": "Formato inválido", "mensagem": "datamov deve estar no formato DD/MM/YYYY"}), 400
      v_dados['datamov'] = v_data_objeto

      v_nova_movimentacao = MovimentacaoOS(**v_dados)
        
      try:
          db.session.add(v_nova_movimentacao)
          db.session.commit()
          return jsonify({"mensagem": "Sucesso", "id": v_nova_movimentacao.id}), 201
      except (TypeError, ValueError) as e:
          db.session.rollback()
          return jsonify({
              "erro": "Tipo de dado inválido", 
              "mensagem": "Um ou mais campos possuem valores incompatíveis com o banco de dados"
          }), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)

          if 'Cannot add or update a child row' in v_erro_str or 'FOREIGN KEY constraint failed' in v_erro_str:
              return jsonify({
                  "erro": "Erro de consistência",
                  "mensagem": "O 'idos' ou 'idcolaborador' informado não existe na base de dados"
              }), 409
          
          return jsonify({"erro": "Erro de integridade", "detalhes": str(e.orig)}), 400     
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Os/Movimentacao/<int:id>', methods=['GET'])
  @login_required
  def f_read_movimentacao_os(id):
      """
      Busca uma movimentação de OS específica pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_movimentacao = db.session.get(MovimentacaoOS, id)
      if not v_movimentacao:
          return jsonify({"erro": "Não encontrado", "mensagem": "Movimentação não encontrada"}), 404
      
      return jsonify(v_movimentacao.f_para_dicionario()), 200

  @v_app.route('/Os/Movimentacao/get/<int:idos>', methods=['GET'])
  @login_required
  def f_read_all_movimentacoes_os(idos):
      """
      Lista todas as movimentações vinculadas a uma ordem de serviço específica
      ---
      parameters:
        - name: idos
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        500:
          description:
      """
      try:
          v_movimentacoes = MovimentacaoOS.query.filter_by(idos=idos).all()

          return jsonify([v_m.f_para_dicionario() for v_m in v_movimentacoes]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Os/Movimentacao/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_movimentacao_os(id):
      """
      Atualiza os dados de uma movimentação de OS existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              idos:
                type: integer
                example: 2
              idcolaborador:
                type: integer
                example: 2
              datamov:
                type: string
                example: "22/05/2026"
              descricao:
                type: string
                example: "Descrição da movimentação devidamente atualizada pelo supervisor"
              visivel:
                type: integer
                example: 1
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_movimentacao = db.session.get(MovimentacaoOS, id)

      if not v_movimentacao:
          return jsonify({"erro": "Não encontrado", "mensagem": "Movimentação não encontrada"}), 404
      
      v_novos_dados = request.get_json(silent=True)
      if v_novos_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400
      
      v_campos_permitidos = ['idos', 'idcolaborador', 'datamov', 'descricao', 'visivel']

      try:
          for v_chave, v_valor in v_novos_dados.items():
              if v_chave in v_campos_permitidos:
                  if v_chave in ['idos', 'visivel'] and v_valor is not None and not isinstance(v_valor, int):
                      raise TypeError(f"O campo {v_chave} deve ser um número inteiro")
                  
                  if v_chave == 'idcolaborador' and v_valor is not None and not isinstance(v_valor, int):
                      raise TypeError("O campo idcolaborador deve ser um número inteiro")

                  if v_chave == 'datamov' and v_valor:
                      v_data_objeto = f_validar_data(v_valor)
                      if not v_data_objeto:
                          return jsonify({"erro": "Data inválida", "mensagem": "Use o formato DD/MM/YYYY"}), 400
                      v_movimentacao.datamov = v_data_objeto
                  else:
                      setattr(v_movimentacao, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except (ValueError, TypeError) as e:
          db.session.rollback()
          return jsonify({
              "erro": "Tipo de dado inválido", 
              "mensagem": "Um ou mais campos possuem valores com tipo incorreto"
          }), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)

          if 'Cannot add or update a child row' in v_erro_str or 'FOREIGN KEY constraint failed' in v_erro_str:
              return jsonify({
                  "erro": "Erro de consistência",
                  "mensagem": "O 'idos' ou 'idcolaborador' informado não existe na base de dados"
              }), 409
          
          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de tipo ou integridade nos dados"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Os/Movimentacao/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_movimentacao_os(id):
      """
      Remove uma movimentação de OS do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_movimentacao = db.session.get(MovimentacaoOS, id)

          if not v_movimentacao:
              return jsonify({"erro": "Não encontrado", "mensagem": "Movimentação não encontrada"}), 404

          db.session.delete(v_movimentacao)
          db.session.commit()
          
          return jsonify({"mensagem": "Removido"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE MODELO DE OS

  @v_app.route('/Os/Modelo/add', methods=['POST'])
  @login_required
  def f_create_modelo_os():
      """
      Cria um novo modelo de ordem de serviço
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: ModeloOS
            required:
              - iddepartamento
              - predescricao
              - descricao
              - peso
              - grupo
            properties:
              iddepartamento:
                type: integer
                example: 1
              predescricao:
                type: string
                maxLength: 100
                example: "Troca de toner de impressora"
              descricao:
                type: string
                example: "Solicitação padrão para substituição de insumos de impressão no setor indicado"
              peso:
                type: integer
                example: 3
              grupo:
                type: integer
                example: 1
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400

          v_campos_obrigatorios = ['iddepartamento', 'predescricao', 'descricao', 'peso', 'grupo']
          for v_campo in v_campos_obrigatorios:
              if v_dados.get(v_campo) is None or str(v_dados.get(v_campo)).strip() == "":
                  return jsonify({
                      "erro": "Campos ausentes", 
                      "mensagem": f"O campo '{v_campo}' é obrigatório e não pode ser nulo ou vazio"
                  }), 400

          if not isinstance(v_dados.get('iddepartamento'), int):
              raise TypeError("O campo 'iddepartamento' deve ser um número inteiro")
          if not isinstance(v_dados.get('peso'), int):
              raise TypeError("O campo 'peso' deve ser um número inteiro")
          if not isinstance(v_dados.get('grupo'), int):
              raise TypeError("O campo 'grupo' deve ser um número inteiro")

          v_novo_modelo = ModeloOS(
              iddepartamento=v_dados.get('iddepartamento'),
              predescricao=v_dados.get('predescricao').strip(),
              descricao=v_dados.get('descricao'),
              peso=v_dados.get('peso'),
              grupo=v_dados.get('grupo')
          )

          db.session.add(v_novo_modelo)
          db.session.flush()
          db.session.commit()

          return jsonify({
              "mensagem": "Modelo de ordem de serviço criado com sucesso",
              "id": v_novo_modelo.id
          }), 201
      except TypeError as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)

          if 'a foreign key constraint fails' in v_erro_str.lower() or 'foreign key constraint failed' in v_erro_str.lower():
              return jsonify({
                  "erro": "Conflito de integridade", 
                  "mensagem": "O 'iddepartamento' informado não existe na base de dados"
              }), 409
          
          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de consistência ao salvar o modelo"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Os/Modelo/get/<int:id>', methods=['GET'])
  @login_required
  def f_read_modelo_os(id):
      """
      Busca um modelo de OS específico pelo ID
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_modelo = db.session.get(ModeloOS, id)
      if not v_modelo:
          return jsonify({"erro": "Não encontrado", "mensagem": "Modelo de OS não encontrado"}), 404
      
      return jsonify(v_modelo.f_para_dicionario()), 200


  @v_app.route('/Os/Modelo/get', methods=['GET'])
  @login_required
  def f_read_all_modelos_os():
      """
      Lista todos os modelos de OS cadastrados no sistema
      ---
      responses:
        200:
          description:
        500:
          description:
      """
      try:
          v_modelos = ModeloOS.query.all()

          return jsonify([v_m.f_para_dicionario() for v_m in v_modelos]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Os/Modelo/upd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_modelo_os(id):
      """
      Atualiza dados de um modelo de OS existente
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              iddepartamento:
                type: integer
                example: 2
              predescricao:
                type: string
                example: "Troca de toner editada"
              descricao:
                type: string
                example: "Nova descrição do template"
              peso:
                type: integer
                example: 2
              grupo:
                type: integer
                example: 1
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_modelo = db.session.get(ModeloOS, id)

      if not v_modelo:
          return jsonify({"erro": "Não encontrado", "mensagem": "Modelo de OS não encontrado"}), 404
      
      v_novos_dados = request.get_json(silent=True)
      if v_novos_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400
      
      v_campos_permitidos = ['iddepartamento', 'predescricao', 'descricao', 'peso', 'grupo']

      try:
          for v_chave, v_valor in v_novos_dados.items():
              if v_chave in v_campos_permitidos:
                  if v_chave in ['iddepartamento', 'peso', 'grupo'] and v_valor is not None and not isinstance(v_valor, int):
                      raise TypeError(f"O campo '{v_chave}' deve ser um número inteiro")
                  
                  if v_chave == 'predescricao' and v_valor is not None:
                      setattr(v_modelo, v_chave, str(v_valor).strip())
                  else:
                      setattr(v_modelo, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except (ValueError, TypeError) as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig)

          if 'foreign key constraint fails' in v_erro_str.lower() or 'foreign key constraint failed' in v_erro_str.lower():
              return jsonify({
                  "erro": "Erro de consistência",
                  "mensagem": "O 'iddepartamento' informado não existe na base de dados"
              }), 409
          
          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de tipo ou integridade nos dados"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Os/Modelo/del/<int:id>', methods=['DELETE'])
  @login_required
  def f_delete_modelo_os(id):
      """
      Remove um modelo de OS do sistema
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_modelo = db.session.get(ModeloOS, id)

          if not v_modelo:
              return jsonify({"erro": "Não encontrado", "mensagem": "Modelo de OS não encontrado"}), 404
            
          db.session.delete(v_modelo)
          db.session.commit()
          return jsonify({"mensagem": "Removido"}), 200   
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE AGENDAMENTO DE OS

  @v_app.route('/Os/Agendamento/add', methods=['POST'])
  @login_required
  def f_create_os_agendamento():
      """
      Cria uma nova configuração de agendamento de OS
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: OSAgendamento
            required:
              - idempresa
              - idmodelo
              - intervalo
              - estado
            properties:
              idempresa:
                type: integer
                example: 2
              idmodelo:
                type: integer
                example: 1
              intervalo:
                type: integer
                example: 30
              estado:
                type: boolean
                example: true
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400

          v_campos_obrigatorios = ['idempresa', 'idmodelo', 'intervalo', 'estado']
          for v_campo in v_campos_obrigatorios:
              if v_dados.get(v_campo) is None or str(v_dados.get(v_campo)).strip() == "":
                  return jsonify({
                      "erro": "Campos ausentes", 
                      "mensagem": f"O campo '{v_campo}' é obrigatório e não pode ser nulo ou vazio"
                  }), 400

          if not isinstance(v_dados.get('idempresa'), int):
              raise TypeError("O campo 'idempresa' deve ser um número inteiro")
          if not isinstance(v_dados.get('idmodelo'), int):
              raise TypeError("O campo 'idmodelo' deve ser um número inteiro")
          if not isinstance(v_dados.get('intervalo'), int):
              raise TypeError("O campo 'intervalo' deve ser um número inteiro")
          if not isinstance(v_dados.get('estado'), bool):
              raise TypeError("O campo 'estado' deve ser um valor booleano (true/false)")

          v_novo_agendamento = OSAgendamento(
              idempresa=v_dados.get('idempresa'),
              idmodelo=v_dados.get('idmodelo'),
              intervalo=v_dados.get('intervalo'),
              estado=v_dados.get('estado')
          )

          db.session.add(v_novo_agendamento)
          db.session.flush()
          db.session.commit()

          return jsonify({
              "mensagem": "Agendamento de ordem de serviço criado com sucesso",
              "idagendamento": v_novo_agendamento.idagendamento
          }), 201
      except TypeError as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig).lower()

          if (hasattr(e.orig, 'args') and e.orig.args[0] == 1452) or \
             'foreign key' in v_erro_str or \
             'chave estrangeira' in v_erro_str:
              return jsonify({
                  "erro": "Conflito de integridade", 
                  "mensagem": "A 'idempresa' ou 'idmodelo' informada não existe na base de dados"
              }), 409
              
          return jsonify({
              "erro": "Dados inválidos", 
              "mensagem": "Erro de consistência ao salvar o agendamento"
          }), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
  
  @v_app.route('/Os/Agendamento/get/<int:idagendamento>', methods=['GET'])
  @login_required
  def f_read_os_agendamento(idagendamento):
      """
      Busca uma configuração de agendamento de OS específica pelo ID
      ---
      parameters:
        - name: idagendamento
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
      """
      v_agendamento = db.session.get(OSAgendamento, idagendamento)
      if not v_agendamento:
          return jsonify({"erro": "Não encontrado", "mensagem": "Agendamento de OS não encontrado"}), 404
      
      return jsonify(v_agendamento.f_para_dicionario()), 200

  @v_app.route('/Os/Agendamento/get', methods=['GET'])
  @login_required
  def f_read_all_os_agendamentos():
      """
      Lista todas as configurações de agendamento de OS do sistema
      ---
      responses:
        200:
          description:
        500:
          description:
      """
      try:
          v_agendamentos = OSAgendamento.query.all()

          return jsonify([v_a.f_para_dicionario() for v_a in v_agendamentos]), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Os/Agendamento/upd/<int:idagendamento>', methods=['PUT'])
  @login_required
  def f_update_os_agendamento(idagendamento):
      """
      Atualiza uma configuração de agendamento de OS existente
      ---
      parameters:
        - name: idagendamento
          in: path
          type: integer
          required: true
        - name: body
          in: body
          required: true
          schema:
            properties:
              idempresa:
                type: integer
                example: 2
              idmodelo:
                type: integer
                example: 1
              intervalo:
                type: integer
                example: 15
              estado:
                type: boolean
                example: false
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        409:
          description:
        500:
          description:
      """
      v_agendamento = db.session.get(OSAgendamento, idagendamento)

      if not v_agendamento:
          return jsonify({"erro": "Não encontrado", "mensagem": "Agendamento de OS não encontrado"}), 404
      
      v_novos_dados = request.get_json(silent=True)
      if v_novos_dados is None:
          return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400
      
      v_campos_permitidos = ['idempresa', 'idmodelo', 'intervalo', 'estado']

      try:
          for v_chave, v_valor in v_novos_dados.items():
              if v_chave in v_campos_permitidos:
                  if v_chave in ['idempresa', 'idmodelo', 'intervalo'] and v_valor is not None and not isinstance(v_valor, int):
                      raise TypeError(f"O campo '{v_chave}' deve ser um número inteiro")
                  
                  if v_chave == 'estado' and v_valor is not None and not isinstance(v_valor, bool):
                      raise TypeError("O campo 'estado' deve ser um valor booleano (true/false)")

                  setattr(v_agendamento, v_chave, v_valor)

          db.session.flush()
          db.session.commit()
          return jsonify({"mensagem": "Atualizado com sucesso"}), 200
      except (ValueError, TypeError) as e:
          db.session.rollback()
          return jsonify({"erro": "Tipo de dado inválido", "mensagem": str(e)}), 400
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e.orig).lower()

          if 'foreign key constraint fails' in v_erro_str or 'foreign key constraint failed' in v_erro_str:
              return jsonify({
                  "erro": "Erro de consistência",
                  "mensagem": "A 'idempresa' ou 'idmodelo' informada não existe na base de dados"
              }), 409
          
          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de consistência ou integridade nos dados"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Os/Agendamento/del/<int:idagendamento>', methods=['DELETE'])
  @login_required
  def f_delete_os_agendamento(idagendamento):
      """
      Remove uma configuração de agendamento de OS do sistema
      ---
      parameters:
        - name: idagendamento
          in: path
          type: integer
          required: true
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_agendamento = db.session.get(OSAgendamento, idagendamento)

          if not v_agendamento:
              return jsonify({"erro": "Não encontrado", "mensagem": "Agendamento de OS não encontrado"}), 404
            
          db.session.delete(v_agendamento)
          db.session.commit()
          return jsonify({"mensagem": "Removido"}), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE VISUALIZAÇÃO DE AVISO

  @v_app.route('/Aviso/Visto/add', methods=['POST'])
  @login_required
  def f_create_visto_aviso():
      """
      Registra a visualização de um colaborador em uma ordem de serviço
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: VistoAvisos
            required:
              - idos
              - idcolaborador
            properties:
              idos:
                type: integer
                example: 1
              idcolaborador:
                type: integer
                example: 2
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({
                  "erro": "Requisição inválida", 
                  "mensagem": "O corpo da requisição deve ser um JSON válido"
              }), 400

          v_campos_obrigatorios = ['idos', 'idcolaborador']
          for v_campo in v_campos_obrigatorios:
              if v_dados.get(v_campo) is None or str(v_dados.get(v_campo)).strip() == "":
                  return jsonify({
                      "erro": "Campos ausentes", 
                      "mensagem": f"O campo '{v_campo}' é obrigatório e não pode ser nulo ou vazio"
                  }), 400

          if not isinstance(v_dados.get('idos'), int) or not isinstance(v_dados.get('idcolaborador'), int):
              return jsonify({"erro": "Tipo de dado inválido", "mensagem": "Os campos devem ser números inteiros"}), 400

          v_os_existe = db.session.get(OrdemServico, v_dados.get('idos'))
          v_colab_existe = db.session.get(Colaborador, v_dados.get('idcolaborador'))
      
          if not v_os_existe or not v_colab_existe:
              return jsonify({
                  "erro": "Conflito de integridade", 
                  "mensagem": "A 'idos' ou o 'idcolaborador' não existe na base de dados"
              }), 409
          
          # Como VistoAvisos é um db.Table, o insert é feito direto pela session
          db.session.execute(
              db.insert(VistoAvisos).values(
                  idOs=v_dados.get('idos'),
                  idColaborador=v_dados.get('idcolaborador')
              )
          )
          db.session.commit()

          return jsonify({
              "mensagem": "Visualização da ordem de serviço registrada com sucesso"
          }), 201
      except IntegrityError as e:
          db.session.rollback()
          v_erro_str = str(e).lower()

          if (hasattr(e, 'orig') and hasattr(e.orig, 'args') and e.orig.args[0] == 1062) or \
            'unique' in v_erro_str or 'duplicate' in v_erro_str or 'duplicada' in v_erro_str:
              return jsonify({
                  "erro": "Conflito de dados", 
                  "mensagem": "Este colaborador já registrou visualização para esta ordem de serviço"
              }), 409

          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de consistência ao salvar"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
  
  # Endpoint polimórfico
  @v_app.route('/Aviso/Visto/get', methods=['GET'])
  @login_required
  def f_read_vistos_aviso():
      """
      Busca uma visualização específica, ou lista todas se nenhum parâmetro for passado
      ---
      parameters:
        - name: idos
          in: query
          type: integer
          required: false
          description: ID da ordem de serviço (para busca individual)
        - name: idcolaborador
          in: query
          type: integer
          required: false
          description: ID do colaborador (para busca individual)
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_idos_str = request.args.get('idos')
          v_idcolaborador_str = request.args.get('idcolaborador')

          # Read all (nenhum parâmetro enviado pelo usuário)
          if not v_idos_str and not v_idcolaborador_str:
              v_resultados = db.session.query(VistoAvisos).all()
              v_lista_avisos = [
                  {
                      "idos": v_linha.idOs,
                      "idcolaborador": v_linha.idColaborador
                  }
                  for v_linha in v_resultados
              ]
              return jsonify(v_lista_avisos), 200

          # Read (parâmetros enviados pelo usuário)
          if not v_idos_str or not v_idcolaborador_str:
              return jsonify({
                  "erro": "Campos ausentes",
                  "mensagem": "Para busca individual, informe 'idos' e 'idcolaborador' juntos"
              }), 400

          try:
              v_idos = int(v_idos_str)
              v_idcolaborador = int(v_idcolaborador_str)
          except ValueError:
              return jsonify({"erro": "Tipo inválido", "mensagem": "Os IDs devem ser inteiros"}), 400

          v_comando = VistoAvisos.select().where(
              (VistoAvisos.c.idOs == v_idos) & 
              (VistoAvisos.c.idColaborador == v_idcolaborador)
          )
          v_resultado = db.session.execute(v_comando).first()

          if not v_resultado:
              return jsonify({
                  "erro": "Não encontrado",
                  "mensagem": "Este registro de visualização não existe"
              }), 404

          return jsonify({
              "idos": v_resultado.idOs,
              "idcolaborador": v_resultado.idColaborador
          }), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # Não há update pois não faz sentido neste escopo; o ideal é criar um novo registro, ou deletar um antigo caso seja necessário por alguma razão

  @v_app.route('/Aviso/Visto/del', methods=['DELETE'])
  @login_required
  def f_delete_visto_aviso():
      """
      Remove o registro de visualização de uma ordem de serviço
      ---
      parameters:
        - name: idos
          in: query
          type: integer
          required: true
          description: ID da ordem de serviço
          example: 1
        - name: idcolaborador
          in: query
          type: integer
          required: true
          description: ID do colaborador
          example: 2
      responses:
        200:
          description:
        400:
          description:
        404:
          description: 
        500:
          description:
      """
      try:
          v_idos_str = request.args.get('idos')
          v_idcolaborador_str = request.args.get('idcolaborador')

          if not v_idos_str or not v_idcolaborador_str:
              return jsonify({
                  "erro": "Campos ausentes",
                  "mensagem": "Os parâmetros 'idos' e 'idcolaborador' são obrigatórios na URL"
              }), 400

          try:
              v_idos = int(v_idos_str)
              v_idcolaborador = int(v_idcolaborador_str)
          except ValueError:
              return jsonify({
                  "erro": "Tipo de dado inválido",
                  "mensagem": "Os parâmetros 'idos' e 'idcolaborador' devem ser números inteiros"
              }), 400

          v_comando = VistoAvisos.delete().where(
              (VistoAvisos.c.idOs == v_idos) & 
              (VistoAvisos.c.idColaborador == v_idcolaborador)
          )
          v_resultado = db.session.execute(v_comando)
          db.session.commit()

          if v_resultado.rowcount == 0:
              return jsonify({
                  "erro": "Não encontrado",
                  "mensagem": "Este registro de visualização não existe na base de dados"
              }), 404

          return jsonify({
              "mensagem": "Visualização da ordem de serviço removida com sucesso"
          }), 200

      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINTS DE AVISO DE OS

  @v_app.route('/Aviso/os/add', methods=['POST'])
  @login_required
  def f_create_aviso():
      """
      Registra um novo aviso para uma ordem de serviço
      ---
      parameters:
        - name: body
          in: body
          required: true
          schema:
            id: AvisoOS
            required:
              - idos
              - origem
            properties:
              idos:
                type: integer
                example: 1
              origem:
                type: integer
                example: 2
              analitico:
                type: boolean
                example: false
      responses:
        201:
          description:
        400:
          description:
        409:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400

          v_campos_obrigatorios = ['idos', 'origem']
          for v_campo in v_campos_obrigatorios:
              if v_dados.get(v_campo) is None or str(v_dados.get(v_campo)).strip() == "":
                  return jsonify({"erro": "Campos ausentes", "mensagem": f"O campo '{v_campo}' é obrigatório"}), 400

          if not isinstance(v_dados.get('idos'), int) or not isinstance(v_dados.get('origem'), int):
              return jsonify({"erro": "Tipo de dado inválido", "mensagem": "Os campos 'idos' e 'origem' devem ser números inteiros"}), 400

          v_analitico = v_dados.get('analitico', False)
          if not isinstance(v_analitico, bool):
              v_analitico = bool(v_analitico)

          v_os_existe = db.session.get(OrdemServico, v_dados.get('idos'))
          if not v_os_existe:
              return jsonify({
                  "erro": "Conflito de integridade", 
                  "mensagem": "A ordem de serviço ('idos') informada não existe na base de dados"
              }), 409

          v_novo_aviso = AvisoOS(
              idos=v_dados.get('idos'),
              origem=v_dados.get('origem'),
              analitico=v_analitico
          )
          
          db.session.add(v_novo_aviso)
          db.session.commit()

          return jsonify({
              "mensagem": "Aviso registrado com sucesso",
              "aviso": v_novo_aviso.f_para_dicionario()
          }), 201
      except IntegrityError:
          db.session.rollback()
          return jsonify({"erro": "Dados inválidos", "mensagem": "Erro de consistência ao salvar o aviso"}), 400
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Aviso/os/<int:idaviso>', methods=['GET'])
  @login_required
  def f_read_aviso(idaviso):
      """
      Busca um aviso de ordem de serviço específico pelo seu ID
      ---
      parameters:
        - name: idaviso
          in: path
          type: integer
          required: true
          description: ID do aviso a ser consultado
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_aviso = db.session.get(AvisoOS, idaviso)

          if not v_aviso:
              return jsonify({
                  "erro": "Não encontrado",
                  "mensagem": f"O aviso com ID {idaviso} não existe"
              }), 404

          return jsonify(v_aviso.f_para_dicionario()), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Aviso/os/get/<int:idos>', methods=['GET'])
  @login_required
  def f_read_all_avisos(idos):
      """
      Lista todos os avisos vinculados a uma ordem de serviço específica
      ---
      parameters:
        - name: idos
          in: path
          type: integer
          required: true
          description: ID da ordem de serviço para listar os avisos
      responses:
        200:
          description:
        500:
          description:
      """
      try:
          v_resultados = db.session.query(AvisoOS).filter_by(idos=idos).all()

          v_lista_avisos = [v_aviso.f_para_dicionario() for v_aviso in v_resultados]

          return jsonify(v_lista_avisos), 200
      except Exception as e:
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  @v_app.route('/Aviso/os/upd/<int:idaviso>', methods=['PUT'])
  @login_required
  def f_update_aviso(idaviso):
      """
      Atualiza os dados de um aviso de ordem de serviço existente
      ---
      parameters:
        - name: idaviso
          in: path
          type: integer
          required: true
          description: ID do aviso a ser atualizado
        - name: body
          in: body
          required: true
          schema:
            properties:
              origem:
                type: integer
                example: 3
              analitico:
                type: boolean
                example: true
      responses:
        200:
          description:
        400:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_dados = request.get_json(silent=True)
          if v_dados is None:
              return jsonify({"erro": "Requisição inválida", "mensagem": "O corpo da requisição deve ser um JSON válido"}), 400

          v_aviso = db.session.get(AvisoOS, idaviso)
          if not v_aviso:
              return jsonify({
                  "erro": "Não encontrado",
                  "mensagem": f"O aviso com ID {idaviso} não foi encontrado para atualização"
              }), 404

          if 'origem' in v_dados:
              v_origem = v_dados.get('origem')
              if v_origem is None or not isinstance(v_origem, int):
                  return jsonify({"erro": "Dado inválido", "mensagem": "O campo 'origem' deve ser um número inteiro"}), 400
              v_aviso.origem = v_origem

          if 'analitico' in v_dados:
              v_analitico = v_dados.get('analitico')
              if not isinstance(v_analitico, bool):
                  return jsonify({"erro": "Dado inválido", "mensagem": "O campo 'analitico' deve ser um booleano (true/false)"}), 400
              v_aviso.analitico = v_analitico

          db.session.commit()

          return jsonify({
              "mensagem": "Aviso atualizado com sucesso",
              "aviso": v_aviso.f_para_dicionario()
          }), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500
      
  @v_app.route('/Aviso/os/del/<int:idaviso>', methods=['DELETE'])
  @login_required
  def f_delete_aviso(idaviso):
      """
      Remove um aviso de ordem de serviço existente
      ---
      parameters:
        - name: idaviso
          in: path
          type: integer
          required: true
          description: ID do aviso a ser deletado
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_aviso = db.session.get(AvisoOS, idaviso)
          
          if not v_aviso:
              return jsonify({
                  "erro": "Não encontrado",
                  "mensagem": f"O aviso com ID {idaviso} não foi encontrado para remoção"
              }), 404

          db.session.delete(v_aviso)
          db.session.commit()

          return jsonify({
              "mensagem": f"Aviso #{idaviso} removido com sucesso"
          }), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  # ENDPOINT DE VALIDAÇÃO DE SENTINELA

  @v_app.route('/Sentinela/Check', methods=['GET'])
  def check_sentinela():
      """
      Valida o acesso externo de um cliente através do seu IP público
      ---
      responses:
        200:
          description:
        401:
          description:
        403:
          description:
        500:
          description:
      """
      try:
          # Obtém o IP do solicitante
          if request.headers.getlist("X-Forwarded-For"):
              v_ip_cliente = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
          else:
              v_ip_cliente = request.remote_addr

          v_acesso = AcessoExterno.query.filter_by(ip=v_ip_cliente).first()

          if not v_acesso:
              return jsonify({
                  "erro": "Acesso negado", 
                  "mensagem": "Acesso externo não configurado para este IP"
              }), 403
          
          v_empresa = v_acesso.empresa
          
          v_sentinela_ativo = (v_acesso.sentinela == 1)
          v_empresa_ativa = (v_empresa is not None and v_empresa.estado is True)

          if v_sentinela_ativo and v_empresa_ativa:
              return jsonify({
                  "sentinela": v_acesso.sentinela,
                  "id_empresa": v_acesso.id_empresa,
                  "razao_empresa": v_empresa.razao
              }), 200
          else:
              v_motivo = "sentinela inativo" if not v_sentinela_ativo else "empresa inativa ou não encontrada"
              return jsonify({
                  "erro": "Validação falhou",
                  "mensagem": f"O acesso foi recusado porque: {v_motivo}",
                  "sentinela": v_acesso.sentinela,
                  "empresa_ativa": v_empresa_ativa
              }), 401
      except Exception as e:
          return jsonify({
              "erro": "Erro interno", 
              "mensagem": str(e)
          }), 500

  # ENDPOINT DE PROTEÇÃO DE SENHA

  @v_app.route('/Usuario/upd/passwd/<int:id>', methods=['PUT'])
  @login_required
  def f_update_user_passwd(id):
      """
      Verifica e corrige a criptografia da senha de um usuário
      ---
      parameters:
        - name: id
          in: path
          type: integer
          required: true
          description: ID único do usuário
      responses:
        200:
          description:
        404:
          description:
        500:
          description:
      """
      try:
          v_usuario = db.session.get(Usuario, id)

          if not v_usuario:
              return jsonify({"erro": "Não encontrado", "mensagem": f"Usuário de ID {id} não existe"}), 404

          v_senha_atual = v_usuario.senha

          # Hashes Werkzeug sempre iniciam com "pbkdf2:", "scrypt:" ou "sha256$"
          v_prefixos_werkzeug = ('pbkdf2:', 'scrypt:', 'sha256$', 'sha1$')
          v_ja_criptografada = v_senha_atual and v_senha_atual.startswith(v_prefixos_werkzeug)

          if v_ja_criptografada:
              return jsonify({
                  "mensagem": "Senha já se encontra no padrão esperado",
                  "id": id
              }), 200

          v_usuario.f_definir_senha(v_senha_atual)

          db.session.flush()
          db.session.commit()

          return jsonify({
              "mensagem": "Senha criptografada e salva com sucesso",
              "id": id
          }), 200
      except Exception as e:
          db.session.rollback()
          return jsonify({"erro": "Erro interno", "mensagem": str(e)}), 500

  return v_app

if __name__ == '__main__':
    app_final = create_app()
    with app_final.app_context():
        db.create_all()
    print("Servidor Waitress iniciando na porta 5000...")
    serve(app_final, host='127.0.0.1', port=5000, threads=6)