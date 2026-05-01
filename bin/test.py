import yaml
from anyio import Path
BASE_DIR = Path(__file__).parent.parent


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
    


struktur_path: Path = BASE_DIR / "config" / "Struktur.yaml"
struktur: dict = load_yaml(struktur_path)



"""
classes: dict = struktur["classes"]
auswahl_classes: list = list(classes.keys())
produkt: dict = struktur["classes"]["Produkt"]
auswahl_produkt: list = struktur["classes"]["Produkt"].keys()
produktbaugruppe: dict = struktur["classes"]["Produkt"]["Produktbaugruppenartikel"]
auswahl_produktbaugruppe:list = struktur["classes"]["Produkt"]["Produktbaugruppenartikel"].keys()
produktoptionsbaugruppe: dict = struktur["classes"]["Produkt"]["Produktbaugruppenartikel"]["Produktoptionsbaugruppenartikel"]
auswahl_produktoptionsbaugruppe: list = struktur["classes"]["Produkt"]["Produktbaugruppenartikel"]["Produktoptionsbaugruppenartikel"].keys()
baugruppe: dict = struktur["classes"]["Produkt"]["Produktbaugruppenartikel"]["Produktoptionsbaugruppenartikel"]["Baugruppenartikel"]
auswahl_baugruppe: list = struktur["classes"]["Produkt"]["Produktbaugruppenartikel"]["Produktoptionsbaugruppenartikel"]["Produktoptionsbaugruppenartikel"]["Baugruppenartikel"].keys()
teileartikel: dict = struktur["Artikelvarianten"]["Teileartikel"]
auswahl_teileartikel: list = struktur["Artikelvarianten"]["Teileartikel"].keys
artikelvarianten: list = struktur["Artikelvarianten"].keys()
"""
auswahl_classes: list = struktur["classes"]
auswahl_produkt: list = struktur["Produkt"]

auswahl_produktbaugruppe:list = struktur["Produktbaugruppenartikel"]
auswahl_produktoptionsbaugruppe: list = struktur["Produktoptionsbaugruppenartikel"]
auswahl_baugruppe: list = struktur["Baugruppenartikel"]
auswahl_teileartikel: list = struktur["Teileartikel"]

auswahl_service: list = struktur["Service"]
auswahl_service_set: list = struktur["Service-Set"]
"""
print(classes)
print(auswahl_produkt)
print(auswahl_produktbaugruppe)
print(auswahl_produktoptionsbaugruppe)
print(auswahl_baugruppe)
print(auswahl_teileartikel)
print(artikelvarianten)
"""

print("classes = ")
print(auswahl_classes)