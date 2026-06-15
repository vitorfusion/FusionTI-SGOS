from database import db

class HotspotTermos(db.Model):
    __tablename__ = 'hotspot_termos'
    registralog = True
    labellog = "Termos de uso do hotspot"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idempresa = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    termos = db.Column(db.Text, nullable=False)

    empresa = db.relationship('Empresa', backref=db.backref('termos_hotspot', lazy=True))

    def f_para_dicionario(self):
        return {
            "id": self.id,
            "idempresa": self.idempresa,
            "termos": self.termos
        }
    
    @property
    def nome(self):
        return self.termos