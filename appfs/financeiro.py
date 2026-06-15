from database import db

class Financeiro(db.Model):
    __tablename__ = 'financeiro'
    registralog = True
    labellog = "Financeiro"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tipo = db.Column(db.String(7))
    descricao = db.Column(db.String(255))
    data = db.Column(db.Date)
    valor = db.Column(db.Float) # Padrão pra precisão dupla de decimais em Python
    os = db.Column(db.Integer, db.ForeignKey('os.id'))
    idusuario = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    situacao = db.Column(db.Integer) # 1: sim, 2: não, 3: cancelado
    df = db.Column(db.Integer, nullable=False, default=0) # Despesa fixa (0 ou 1)
    centrocusto = db.Column(db.Integer, db.ForeignKey('centrocusto.id'), nullable=False)

    relacionamento_centrocusto = db.relationship('CentroCusto')

    def __init__(self, **kwargs):
        super(Financeiro, self).__init__(**kwargs)

    @property
    def nome(self):
        return f"{self.descricao} (R$ {self.valor})"

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "tipo": self.tipo,
            "descricao": self.descricao,
            "data": self.data.strftime('%d/%m/%Y') if self.data else None,
            "valor": self.valor,
            "os": self.os,
            "idusuario": self.idusuario,
            "situacao": self.situacao,
            "df": self.df,
            "centrocusto": self.centrocusto
        }