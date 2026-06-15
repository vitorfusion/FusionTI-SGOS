from database import db

class ColaboradorDepartamento(db.Model):
    __tablename__ = 'colaboradores_departamento'
    registralog = True
    labellog = "Vínculo colaborador-departamento"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idcolaborador = db.Column(db.Integer, db.ForeignKey('colaboradores.id'))
    iddepartamento = db.Column(db.Integer, db.ForeignKey('departamentos.id'))
    scrum = db.Column(db.Integer, nullable=False, default=0)
    
    colaborador = db.relationship('Colaborador', backref=db.backref('departamentos_vinculados', lazy=True))

    # Retorna o nome do colaborador envolvido, para viabilizar os logs
    @property
    def nome(self):
        if self.colaborador:
            return self.colaborador.nome
        return "Colaborador desconhecido"

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "idcolaborador": self.idcolaborador,
            "nome_colaborador": self.nome,
            "iddepartamento": self.iddepartamento,
            "scrum": self.scrum
        }