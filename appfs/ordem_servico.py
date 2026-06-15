from database import db
from datetime import date, datetime, timedelta

class OrdemServico(db.Model):
    __tablename__ = 'os'
    registralog = True
    labellog = "Ordem de serviço"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idagendamento = db.Column(db.Integer, db.ForeignKey('os_agendamento.idagendamento'), nullable=True)
    dataagendamento = db.Column(db.Date, nullable=True) # Não será inserida no create, mas virará obrigatória no update
    horaagendamento = db.Column(db.Time, nullable=True)
    # Data e hora estimadas devem equivaler a data e hora de hoje + peso (1: 24h, 2: 36h, 3: 48h, 4: 60h)
    dataestimada = db.Column(db.Date, nullable=True)
    horaestimada = db.Column(db.Time, nullable=True)
    dataabertura = db.Column(db.Date, nullable=True)
    horaabertura = db.Column(db.Time, nullable=True)
    dataconclusao = db.Column(db.Date, nullable=True)
    horaconclusao = db.Column(db.Time, nullable=True)
    idempresa = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    iddepartamento = db.Column(db.Integer, db.ForeignKey('departamentos.id'), nullable=True)
    idusrempresa = db.Column(db.Integer, db.ForeignKey('usuariosempresa.id'), nullable=True) # Quem abriu a OS
    idcolaborador = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=True) # Quem finalizou a OS
    usrfeedback = db.Column(db.Integer, nullable=True)
    estado = db.Column(db.Boolean, default=True)
    predescricao = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.Text, nullable=False) # longtext no banco
    peso = db.Column(db.Integer, nullable=True) # Peso vai de 1 a 4, sendo que quanto menor o número, mais importante é a tarefa
    usrobservacao = db.Column(db.Text, nullable=True)
    colaborador = db.Column(db.String(50), nullable=True) # Relacionado ao sprint
    flag = db.Column(db.String(255), nullable=True)

    def __init__(self, **kwargs):
        super(OrdemServico, self).__init__(**kwargs)
        self.atualizar_prazos_estimados()

    # Calcula data/hora estimada com base no peso e no momento atual
    def atualizar_prazos_estimados(self):
        v_mapa_horas = {
            1: 24,
            2: 36,
            3: 48,
            4: 60
        }
        
        if self.peso in v_mapa_horas:
            v_horas_adicionais = v_mapa_horas[self.peso]
            v_agora = datetime.now()
            v_momento_estimado = v_agora + timedelta(hours=v_horas_adicionais)
            
            self.dataestimada = v_momento_estimado.date()
            self.horaestimada = v_momento_estimado.time()

    def f_para_dicionario(self):
        v_dict = {}

        for v_col in self.__table__.columns:
            v_valor = getattr(self, v_col.key)

            if v_valor is None:
                v_dict[v_col.key] = None
                continue

            if v_col.key.startswith('data'):
                if isinstance(v_valor, (date, datetime)):
                    v_dict[v_col.key] = v_valor.strftime('%d/%m/%Y')
                else:
                    v_dict[v_col.key] = str(v_valor)
            elif v_col.key.startswith('hora'):
                if hasattr(v_valor, 'strftime'):
                    v_dict[v_col.key] = v_valor.strftime('%H:%M:%S')
                else:
                    v_dict[v_col.key] = str(v_valor)

            else:
                v_dict[v_col.key] = v_valor

        return v_dict
    
    @property
    def nome(self):
        # Retorna a predescrição para o log, ou um "plano B" caso esteja vazia
        return self.predescricao if self.predescricao else f"OS #{self.id}"