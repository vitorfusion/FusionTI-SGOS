from database import db

class HotspotLocal(db.Model):
    __tablename__ = 'hotspot_local'
    registralog = True
    labellog = "Local de hotspot"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_uuid_local_hotspot = db.Column(db.String(100), nullable=False)
    id_empresa = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    descricao = db.Column(db.String(300), nullable=False)
    metodo = db.Column(db.Integer, nullable=False)
    url = db.Column(db.String(400), nullable=True, default=None)
    api_token = db.Column(db.String(600), nullable=True, default=None)
    id_template = db.Column(db.String(300), nullable=True, default=None)

    empresa = db.relationship('Empresa', backref=db.backref('hotspot_locais', lazy=True))

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "id_uuid_local_hotspot": self.id_uuid_local_hotspot,
            "id_empresa": self.id_empresa,
            "descricao": self.descricao,
            "metodo": self.metodo,
            "url": self.url,
            "api_token": self.api_token,
            "id_template": self.id_template
        }
    
    @property
    def nome(self):
        return self.descricao