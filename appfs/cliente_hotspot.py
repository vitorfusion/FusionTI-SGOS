from database import db
from datetime import datetime, date, timezone

class HotspotClient(db.Model):
    __tablename__ = 'hotspot_client'
    registralog = True
    labellog = "Cliente de hotspot"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=True, default=None)
    cpf = db.Column(db.String(11), nullable=True, default=None)
    rg = db.Column(db.String(11), nullable=True, default=None)
    newsletter = db.Column(db.Boolean, nullable=False, default=False)
    idempresa = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    data = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    id_uuid_local_hotspot = db.Column(db.String(100), nullable=True, default=None)
    telefone = db.Column(db.String(100), nullable=True, default=None)

    empresa = db.relationship('Empresa', backref=db.backref('hotspot_clientes', lazy=True))

    def f_para_dicionario(self):
        v_dicionario = {
            v_c.name: getattr(self, v_c.name) 
            for v_c in self.__table__.columns
        }
        
        for v_chave, v_valor in v_dicionario.items():
            if isinstance(v_valor, datetime):
                v_dicionario[v_chave] = v_valor.strftime('%d/%m/%Y %H:%M:%S')
            elif isinstance(v_valor, date):
                v_dicionario[v_chave] = v_valor.strftime('%d/%m/%Y')
                
        return v_dicionario