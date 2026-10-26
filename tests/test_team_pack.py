"""2.19.0 Knowledge Packs carry the offerings catalog and the keyword Keep/Reject learning: install adds offerings
already missing and keeps the larger count per hashed phrase; Undo puts back what was there."""
import os, sys, tempfile, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); os.makedirs(A.CONFIG_DIR)
A.KNOWLEDGE_INFO_FILE = os.path.join(A.CONFIG_DIR, "knowledge_installed.json")
A.KNOWLEDGE_BACKUP_DIR = os.path.join(A.CONFIG_DIR, "knowledge_backups")
A.MODELS_DIR = os.path.join(A.CONFIG_DIR, "models")                 # never touch this copy's real models or data
A.DB_FILE = os.path.join(tmp, "db.csv"); open(A.DB_FILE, "w", encoding="utf-8").write("Term,Category,Definition,Action\nSOW,Acronym,Statement of Work,Include\n")
A.OCR_FIXES_FILE = os.path.join(A.CONFIG_DIR, "ocr_corrections.csv"); A.OCR_IGNORE_FILE = os.path.join(A.CONFIG_DIR, "ocr_ignore.csv")
A.COMPLIANCE_LEARNED_FILE = os.path.join(A.CONFIG_DIR, "compliance_learned.json")
import offerings, keywords
offerings.add("Dream Chaser", "", "Vehicles", "Spaceplane")
offerings.add("LIFE Habitat", "", "Habitats", "Inflatable habitat")
keywords.learn("orbital debris", "Keep"); keywords.learn("orbital debris", "Keep"); keywords.learn("fictional test", "Reject")
import placelearn
placelearn.save_synonyms(placelearn.synonyms_path(A.CONFIG_DIR), "solution, approach\nheat, thermal")    # 2.30.0
pack = os.path.join(tmp, "AcronymHunter_Knowledge_test.zip")
info = A.make_knowledge_pack(pack, "test")
assert "offerings.csv" in info["files"] and "keyword_learning.json" in info["files"], info["files"].keys()
# a second PC: one offering of its own, a smaller count
os.remove(offerings.path()); os.remove(os.path.join(A.CONFIG_DIR, "keyword_learning.json"))
placelearn.save_synonyms(placelearn.synonyms_path(A.CONFIG_DIR), "solution, approach\nrisk, mitigation")
offerings.add("Shooting Star", "", "Vehicles", "Cargo module")
keywords.learn("orbital debris", "Keep")
rep = A.install_knowledge_pack(pack)
names = {o["Offering"] for o in offerings.load()}
assert names == {"Dream Chaser", "LIFE Habitat", "Shooting Star"}, names
L = keywords.learning()
assert L["keep"][keywords.phrase_hash("orbital debris")] == 2 and L["reject"][keywords.phrase_hash("fictional test")] == 1, L
syn = placelearn.load_synonyms(placelearn.synonyms_path(A.CONFIG_DIR))
assert "heat, thermal" in syn and "risk, mitigation" in syn and syn.count("solution, approach") == 1, syn
assert "Section word synonyms: 1 groups added" in rep, rep
assert "Offerings catalog: 2" in rep and "Keyword learning: 2" in rep, rep
assert A.restore_last_knowledge_backup()
assert {o["Offering"] for o in offerings.load()} == {"Shooting Star"}
assert keywords.learning()["keep"][keywords.phrase_hash("orbital debris")] == 1
print("team pack ok")
